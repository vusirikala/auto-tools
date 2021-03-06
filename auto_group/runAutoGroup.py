import os
import sys
import imp
import time
import argparse
import src.sdlpath
import SDLParser as sdl
from SDLang import *
from src.convertToAsymmetric import *
from src.outsrctechniques import SubstituteVar, SubstitutePairings, SplitPairings, HasPairings, \
    CountOfPairings, MaintainOrder, PairInstanceFinderImproved, TestForMultipleEq, GetAttributeVars, \
    GetEquqlityNodes, CountExpOp, CountMulOp, DelAnyVarInList

import codegen_CPP
import codegen_PY

description_text = "sym.-to-asym. conversion for cryptographic schemes in SDL."
parser = argparse.ArgumentParser(description=description_text)
parser.add_argument('-o', '--outfile', help="generate code of new scheme in C++/Python for Charm", required=True)
parser.add_argument('-s', '--sdl', help="input SDL file description of scheme", required=True)
parser.add_argument('-v', '--verbose', help="enable verbose mode", action="store_true")
parser.add_argument('-c', '--config', help="configuration parameters needed for AutoGroup", required=True)
parser.add_argument('-l', '--library', help="which library to benchmark against: miracl or relic", default="miracl")
parser.add_argument('-b', '--benchmark', default=False, help="benchmark AutoGroup execution time", action="store_true")
parser.add_argument('-e', '--estimate', default=False, help="estimate bandwidth for keys and ciphertext/signatures", action="store_true")
parser.add_argument('--short', help="what to minimize: public-keys, secret-keys, assumption, ciphertext, signatures")
parser.add_argument('--path', help="destination for AutoGroup+ output files. Default: current dir")
parser.add_argument('--print', help="print the selected options", default=False, action="store_true")
parser.add_argument('-a', '--autogroup', help="run AutoGroup only (and not AutoGroup+)", default=False, action="store_true")

args = parser.parse_args()
output_file  = args.outfile
sdl_file     = args.sdl
verbose      = args.verbose
config_file  = args.config
library      = args.library
benchmarkOpt = args.benchmark
estimateSize = args.estimate
short_option = args.short
dest_path    = args.path
print_options  = args.print
run_auto_group = args.autogroup

if not dest_path:
    dest_path = ""

if dest_path != "" and dest_path[-1] != '/': dest_path += '/'

if print_options:
    print("\nArguments:")
    print('VERBOSE    :', verbose)
    print('CONFIG     :', config_file)
    print('SDL INPUT  :', sdl_file)
    print('SDL OUTPUT :', output_file)
    print('PATH:      :', dest_path)
    print('BENCHMARK  :', benchmarkOpt)
    print('ESTIMATES  :', estimateSize)
    print('SHORT OPT  :', short_option)

encConfigParams = ["keygenPubVar", "keygenSecVar", "ciphertextVar", "keygenFuncName", "encryptFuncName", "decryptFuncName"]
sigConfigParams = ["keygenPubVar", "keygenSecVar", "signatureVar", "keygenFuncName", "signFuncName", "verifyFuncName"]

def errorOut(keyword):
    sys.exit("configAutoGroup: missing '%s' variable in config." % keyword)

def parseAssumptionFile(cm, assumption_file, verbose, benchmarkOpt, estimateOpt):
    # setup sdl parser configs
    sdl.masterPubVars = cm.assumpMasterPubVars
    sdl.masterSecVars = cm.assumpMasterSecVars
    if not hasattr(cm, "schemeType"):
        sys.exit("configAutoGroup: need to set 'schemeType' in config.")

    #setattr(cm, isAssumption, "true")

    funcOrder = [cm.assumpSetupFuncName, cm.assumpFuncName]
    setattr(cm, functionOrder, funcOrder)

    #TODO: create something like this for assumption?
    #for i in encConfigParams:
    #    if not hasattr(cm, i):
    #        errorOut(i)
    
    if not hasattr(cm, "secparam"):
        secparam = "BN256" # default pairing curve for now
    else:
        secparam = cm.secparam
    
    #do we need this for the assumption?
    dropFirst = None
    if hasattr(cm, "dropFirst"):
        dropFirst = cm.dropFirst
    
    options = {'secparam':secparam, 'userFuncList':[], 'computeSize':estimateOpt, 'dropFirst':dropFirst, 'path':dest_path}

    sdl.parseFile(assumption_file, verbose, ignoreCloudSourcing=True)
    assignInfo_assump = sdl.getAssignInfo()
    assumptionData = {'sdl_name':sdl.assignInfo[sdl.NONE_FUNC_NAME][BV_NAME].getAssignNode().getRight().getAttribute(), 'setting':sdl.assignInfo[sdl.NONE_FUNC_NAME][ALGEBRAIC_SETTING].getAssignNode().getRight().getAttribute(), 'assignInfo':assignInfo_assump, 'typesBlock':sdl.getFuncStmts( TYPES_HEADER ), 'userCodeBlocks':list(set(list(assignInfo_assump.keys())).difference(cm.functionOrder + [TYPES_HEADER, NONE_FUNC_NAME]))}

    if hasattr(cm, "reductionMap"):
        assumptionData['varmap'] = cm.reductionMap

    # this consists of the type of the input scheme (e.g., symmetric)
    setting = sdl.assignInfo[sdl.NONE_FUNC_NAME][ALGEBRAIC_SETTING].getAssignNode().getRight().getAttribute()
    # name of the scheme
    sdl_name = sdl.assignInfo[sdl.NONE_FUNC_NAME][BV_NAME].getAssignNode().getRight().getAttribute()

    typesBlock = sdl.getFuncStmts( TYPES_HEADER )
    info = {'verbose':verbose}

    # we want to ignore user defined functions from our analysis
    # (unless certain variables that we care about are manipulated there)
    userCodeBlocks = list(set(list(assignInfo_assump.keys())).difference(cm.functionOrder + [TYPES_HEADER, NONE_FUNC_NAME]))
    options['userFuncList'] += userCodeBlocks

    lines = list(typesBlock[0].keys())
    lines.sort()
    typesBlockLines = [ i.rstrip() for i in sdl.getLinesOfCodeFromLineNos(lines) ]
    begin = ["BEGIN :: " + TYPES_HEADER]
    end = ["END :: " + TYPES_HEADER]

    # start constructing the preamble for the Asymmetric SDL output
    newLines0 = [ BV_NAME + " := " + sdl_name, SETTING + " := " + sdl.ASYMMETRIC_SETTING ] 
    newLines1 = begin + typesBlockLines + end
    # this fact is already verified by the parser
    # but if scheme claims symmetric
    # and really an asymmetric scheme then parser will
    # complain.
    assert setting == sdl.SYMMETRIC_SETTING, "No need to convert to asymmetric setting."    
    # determine user preference in terms of keygen or encrypt
    short = SHORT_DEFAULT # default option
    if hasattr(cm, 'short'):
        if cm.short in SHORT_OPTIONS:
            short = cm.short
    print("reducing size of '%s'" % short) 

    varTypes = dict(sdl.getVarTypes().get(TYPES_HEADER))
    typesH = dict(varTypes)

    assumptionData['typesH'] = typesH

    if not hasattr(cm, 'schemeType'):
        sys.exit("'schemeType' option missing in specified config file.")
    pairingSearch = []
    # extract the statements, types, dependency list, influence list and exponents of influence list
    # for each algorithm in the SDL scheme
    (stmtS, typesS, depListS, depListNoExpS, infListS, infListNoExpS) = sdl.getVarInfoFuncStmts( cm.assumpSetupFuncName )
    (stmtA, typesA, depListA, depListNoExpA, infListA, infListNoExpA) = sdl.getVarInfoFuncStmts( cm.assumpFuncName )
    varTypes.update(typesS)
    varTypes.update(typesA)

    assumptionData['stmtS'] = stmtS
    assumptionData['stmtA'] = stmtA

    if hasattr(cm, 'graphit') and cm.graphit:
        dg_assump_setup = generateGraph(cm.assumpSetupFuncName, (typesS, depListNoExpS), types.G1, varTypes)
        dg_assump_setup.adjustByMap(assumptionData.get('varmap'))
        dg_assump_itself = generateGraph(cm.assumpFuncName, (typesA, depListNoExpA), types.G1, varTypes)
        dg_assump_itself.adjustByMap(assumptionData.get('varmap'))

        dg_assumption = DotGraph("assumption")
        dg_assumption += dg_assump_setup + dg_assump_itself

        if verbose:
            print("<=== Assumption Instance Graph ===>")
            print(dg_assumption)
            print("<=== Assumption Instance Graph ===>")

        # always record these
        assumptionData['assumptionGraph'] = dg_assumption

    # TODO: expand search to encrypt and potentially setup
    pairingSearch += [stmtS, stmtA] # aka start with decrypt.
            
    info[curveID] = options['secparam']
    info[dropFirstKeyword] = options[dropFirstKeyword]
    gen = Generators(info)
    # JAA: commented out for benchmarking    
    #print("List of generators for scheme")
    # retrieve the generators selected by the scheme
    # typically found in the setup routine in most cases.
    # extract the generators from the setup and keygen routine for later use
    if hasattr(cm, 'assumpSetupFuncName'):
        gen.extractGens(stmtS, typesS)
    if hasattr(cm, 'assumpFuncName'):
        gen.extractGens(stmtA, typesA)
    else:
        sys.exit("Assumption failed: setup not defined for this function. Where to extract generators?")
    generators = gen.getGens()
    # JAA: commented out for benchmarking    
    #print("Generators extracted: ", generators)

    print("\n")

    # need a Visitor class to build these variables  
    # TODO: expand to other parts of algorithm including setup, keygen, encrypt
    # Visits each pairing computation in the SDL and
    # extracts the inputs. This is the beginning of the
    # analysis of these variables as the SDL is converted into
    # an asymmetric scheme.
    hashVarList = []
    pair_vars_G1_lhs = [] 
    pair_vars_G1_rhs = []    
    gpv = GetPairingVariables(pair_vars_G1_lhs, pair_vars_G1_rhs)
    for eachStmt in pairingSearch: # loop through each pairing statement
        lines = eachStmt.keys() # for each line, do the following
        for i in lines:
            if type(eachStmt[i]) == sdl.VarInfo: # make sure we have the Var Object
                # assert that the statement contains a pairing computation
                if HasPairings(eachStmt[i].getAssignNode()):
                    path_applied = []
                    # split pairings if necessary so that we don't influence
                    # the solve in anyway. We can later recombine these during
                    # post processing of the SDL
                    eachStmt[i].assignNode = SplitPairings(eachStmt[i].getAssignNode(), path_applied)
                    # JAA: commented out for benchmarking                    
                    #if len(path_applied) > 0: print("Split Pairings: ", eachStmt[i].getAssignNode())
                    if info['verbose']: print("Each: ", eachStmt[i].getAssignNode())
                    sdl.ASTVisitor( gpv ).preorder( eachStmt[i].getAssignNode() )
                elif eachStmt[i].getHashArgsInAssignNode(): 
                    # in case there's a hashed value...build up list and check later to see if it appears
                    # in pairing variable list
                    hashVarList.append(str(eachStmt[i].getAssignVar()))
                else:
                    continue # not interested
                
    # constraint list narrows the solutions that
    # we care about
    constraintList = []
    # for example, include any hashed values that show up in a pairing by default
    for i in hashVarList:
        if i in pair_vars_G1_lhs or i in pair_vars_G1_rhs:
            constraintList.append(i)
    # JAA: commented out for benchmarking            
    # for each pairing variable, we construct a dependency graph all the way back to
    # the generators used. The input of assignTraceback consists of the list of SDL statements,
    # generators from setup, type info, and the pairing variables.
    # We do this analysis for both sides
    info[ 'G1_lhs' ] = (pair_vars_G1_lhs, assignTraceback(assignInfo_assump, generators, varTypes, pair_vars_G1_lhs, constraintList))
    info[ 'G1_rhs' ] = (pair_vars_G1_rhs, assignTraceback(assignInfo_assump, generators, varTypes, pair_vars_G1_rhs, constraintList))

    depList = {}
    for i in [depListS, depListA]:
        for (key, val) in i.items():
            if(not(len(val) == 0) and not(key == 'input') and not(key == 'output') and not(key in cm.assumpMasterPubVars) and not(key in cm.assumpMasterSecVars)):
                depList[key] = val

    info[ 'deps' ] = (depList, assignTraceback(assignInfo_assump, generators, varTypes, depList, constraintList))

    prunedDeps = {}
    for (key, val) in info['deps'][1].items():
        if(not(len(val) == 0)):
            prunedDeps[key] = val

    the_map = gpv.pairing_map

    assumptionData['info'] = info
    assumptionData['depList'] = depList
    assumptionData['deps'] = info['deps']
    assumptionData['prunedMap'] = prunedDeps
    assumptionData['G1_lhs'] = info['G1_lhs']
    assumptionData['G1_rhs'] = info['G1_rhs']

    assumptionData['the_map'] = the_map

    assumptionData['options'] = options

    assumptionData['gpv'] = gpv

    assumptionData['gen'] = gen

    assumptionData['varTypes'] = varTypes

    #prune varTypes to remove ZR that we don't care about
    additionalDeps = dict(list(assumptionData['info']['deps'][0].items()))
    items = []
    newlist = []
    newDeps = {}
    for (key,val) in additionalDeps.items():
        #items = list(additionalDeps[key])
        newlist = []
        for j in val:
            if((sdl.getVarTypeFromVarName(j, None, True) == types.G1) or (sdl.getVarTypeFromVarName(j, None, True) == types.G2)):
                newlist.append(j)
        if(not(len(set(newlist)) == 0)):
            if(key in assumptionData['varmap']):
                newDeps[assumptionData['varmap'][key]] = set(newlist)
            else:
                newDeps[key] = set(newlist)
    assumptionData['newDeps'] = newDeps

    assumptionData['assumptionFile'] = assumption_file
    assumptionData['config'] = cm

    assumptionData['options']['type'] = "assumption"
    assumptionData['newLines0'] = newLines0

    return assumptionData

def parseReductionFile(cm, reduction_file, verbose, benchmarkOpt, estimateOpt):
    # setup sdl parser configs
    sdl.masterPubVars = cm.reducMasterPubVars
    sdl.masterSecVars = cm.reducMasterSecVars
    if not hasattr(cm, "schemeType"):
        sys.exit("configAutoGroup: need to set 'schemeType' in config.")

    if cm.schemeType == PKENC:
        funcOrder = [cm.reducSetupFuncName, cm.reducQueryFuncName, cm.reducChallengeFuncName]
        setattr(cm, functionOrder, funcOrder)
    elif cm.schemeType == PKSIG:
        funcOrder = [cm.reducSetupFuncName, cm.reducQueryFuncName]
        setattr(cm, functionOrder, funcOrder)
    else:
        sys.exit("configAutoGroup: unrecognized 'schemeType' in config.")

    #TODO: create something like this for assumption?
    #for i in encConfigParams:
    #    if not hasattr(cm, i):
    #        errorOut(i)
    
    if not hasattr(cm, "secparam"):
        secparam = "BN256" # default pairing curve for now
    else:
        secparam = cm.secparam
    
    #do we need this for the assumption?
    dropFirst = None
    if hasattr(cm, "dropFirst"):
        dropFirst = cm.dropFirst
    
    options = {'secparam':secparam, 'userFuncList':[], 'computeSize':estimateOpt, 'dropFirst':dropFirst, 'path':dest_path}

    sdl.parseFile(reduction_file, verbose, ignoreCloudSourcing=True)
    assignInfo_reduction = sdl.getAssignInfo()
    reductionData = {'sdl_name':sdl.assignInfo[sdl.NONE_FUNC_NAME][BV_NAME].getAssignNode().getRight().getAttribute(), 'setting':sdl.assignInfo[sdl.NONE_FUNC_NAME][ALGEBRAIC_SETTING].getAssignNode().getRight().getAttribute(), 'assignInfo':assignInfo_reduction, 'typesBlock':sdl.getFuncStmts( TYPES_HEADER ), 'userCodeBlocks':list(set(list(assignInfo_reduction.keys())).difference(cm.functionOrder + [TYPES_HEADER, NONE_FUNC_NAME]))}

    if hasattr(cm, "reductionMap"):
        reductionData['varmap'] = cm.reductionMap

    # this consists of the type of the input scheme (e.g., symmetric)
    setting = sdl.assignInfo[sdl.NONE_FUNC_NAME][ALGEBRAIC_SETTING].getAssignNode().getRight().getAttribute()
    # name of the scheme
    sdl_name = sdl.assignInfo[sdl.NONE_FUNC_NAME][BV_NAME].getAssignNode().getRight().getAttribute()

    typesBlock = sdl.getFuncStmts( TYPES_HEADER )
    info = {'verbose':verbose}

    # we want to ignore user defined functions from our analysis
    # (unless certain variables that we care about are manipulated there)
    userCodeBlocks = list(set(list(assignInfo_reduction.keys())).difference(cm.functionOrder + [TYPES_HEADER, NONE_FUNC_NAME]))
    options['userFuncList'] += userCodeBlocks

    lines = list(typesBlock[0].keys())
    lines.sort()
    typesBlockLines = [ i.rstrip() for i in sdl.getLinesOfCodeFromLineNos(lines) ]
    begin = ["BEGIN :: " + TYPES_HEADER]
    end = ["END :: " + TYPES_HEADER]

    # start constructing the preamble for the Asymmetric SDL output
    newLines0 = [ BV_NAME + " := " + sdl_name, SETTING + " := " + sdl.ASYMMETRIC_SETTING ] 
    newLines1 = begin + typesBlockLines + end
    # this fact is already verified by the parser
    # but if scheme claims symmetric
    # and really an asymmetric scheme then parser will
    # complain.
    assert setting == sdl.SYMMETRIC_SETTING, "No need to convert to asymmetric setting."    
    # determine user preference in terms of keygen or encrypt
    short = SHORT_DEFAULT # default option
    if hasattr(cm, 'short'):
        if cm.short in SHORT_OPTIONS:
            short = cm.short
    print("reducing size of '%s'" % short) 

    varTypes = dict(sdl.getVarTypes().get(TYPES_HEADER))
    typesH = dict(varTypes)

    reductionData['typesH'] = typesH

    if not hasattr(cm, 'schemeType'):
        sys.exit("'schemeType' option missing in specified config file.")
    pairingSearch = []
    # extract the statements, types, dependency list, influence list and exponents of influence list
    # for each algorithm in the SDL scheme
    if cm.schemeType == PKENC:
        (stmtS, typesS, depListS, depListNoExpS, infListS, infListNoExpS) = sdl.getVarInfoFuncStmts( cm.reducSetupFuncName )
        (stmtQ, typesQ, depListQ, depListNoExpQ, infListQ, infListNoExpQ) = sdl.getVarInfoFuncStmts( cm.reducQueryFuncName )
        (stmtC, typesC, depListC, depListNoExpC, infListC, infListNoExpC) = sdl.getVarInfoFuncStmts( cm.reducChallengeFuncName )
        depListData = {cm.reducChallengeFuncName: depListNoExpC, cm.reducQueryFuncName: depListNoExpQ, cm.reducSetupFuncName: depListNoExpS}
        varTypes.update(typesS)
        varTypes.update(typesQ)
        varTypes.update(typesC)

        if hasattr(cm, 'graphit') and cm.graphit and cm.single_reduction:
            dg_reduc_setup = generateGraphForward(cm.reducSetupFuncName, (stmtS, typesS, infListNoExpS))
            dg_reduc_setup.adjustByMap(reductionData.get('varmap'))
            dg_reduc_query = generateGraph(cm.reducQueryFuncName, (typesQ, depListNoExpQ), types.G1, varTypes)
            dg_reduc_query.adjustByMap(reductionData.get('varmap'))
            dg_reduc_chall = generateGraph(cm.reducChallengeFuncName, (typesC, depListNoExpC), types.G1, varTypes)
            dg_reduc_chall.adjustByMap(reductionData.get('varmap'))

            if verbose:
                print("<=== Reduction Setup Graph ===>")
                print(dg_reduc_setup)
                print("<=== Reduction Setup Graph ===>")

                print("<=== Reduction Query Graph ===>")
                print(dg_reduc_query)
                print("<=== Reduction Query Graph ===>")

                print("<=== Reduction Challenge Graph ===>")
                print(dg_reduc_chall)
                print("<=== Reduction Challenge Graph ===>")

            dg_reduction = DotGraph("reduction")
            dg_reduction += dg_reduc_setup + dg_reduc_query + dg_reduc_chall
            if verbose:
                print("<=== Reduction Graph ===>")
                print(dg_reduction)
                print("<=== Reduction Graph ===>")

            reductionData['reductionGraph'] = dg_reduction

        # TODO: expand search to encrypt and potentially setup
        pairingSearch += [stmtS, stmtQ, stmtC] # aka start with decrypt.
                
        info[curveID] = options['secparam']
        info[dropFirstKeyword] = options[dropFirstKeyword]
        gen = Generators(info)
        # JAA: commented out for benchmarking    
        #print("List of generators for scheme")
        # retrieve the generators selected by the scheme
        # typically found in the setup routine in most cases.
        # extract the generators from the setup and keygen routine for later use
        if hasattr(cm, 'reducSetupFuncName'):
            gen.extractGens(stmtS, typesS)
        if hasattr(cm, 'reducQueryFuncName'):
            gen.extractGens(stmtQ, typesQ)
        if hasattr(cm, 'reducChallengeFuncName'):
            gen.extractGens(stmtC, typesC)
        else:
            sys.exit("Assumption failed: setup not defined for this function. Where to extract generators?")
        generators = gen.getGens()
        # JAA: commented out for benchmarking    
        #print("Generators extracted: ", generators)
    elif cm.schemeType == PKSIG:
        (stmtS, typesS, depListS, depListNoExpS, infListS, infListNoExpS) = sdl.getVarInfoFuncStmts( cm.reducSetupFuncName )
        (stmtQ, typesQ, depListQ, depListNoExpQ, infListQ, infListNoExpQ) = sdl.getVarInfoFuncStmts( cm.reducQueryFuncName )
        depListData = { cm.reducQueryFuncName: depListNoExpQ, cm.reducSetupFuncName: depListNoExpS}

        varTypes.update(typesS)
        varTypes.update(typesQ)

        if hasattr(cm, 'graphit') and cm.graphit:
            dg_reduc_setup = generateGraphForward(cm.reducSetupFuncName, (stmtS, typesS, infListNoExpS))
            dg_reduc_setup.adjustByMap(reductionData.get('varmap'))

            #dg_reduc_query = generateGraphForward(cm.reducQueryFuncName, (stmtQ, typesQ, infListNoExpQ))
            #dg_reduc_query.adjustByMap(reductionData.get('varmap'))

            new_depListNoExpQ = simplifyDepMap(stmtQ, typesQ, infListNoExpQ, depListNoExpQ)
            dg_reduc_query = generateGraph(cm.reducQueryFuncName, (typesQ, new_depListNoExpQ), types.G1, varTypes)
            dg_reduc_query.adjustByMap(reductionData.get('varmap'))

            if verbose:
                print("<=== Reduction Setup Graph ===>")
                print(dg_reduc_setup)
                print("<=== Reduction Setup Graph ===>")

                print("<=== Reduction Query Graph (backward) ===>")
                print(dg_reduc_query)
                print("<=== Reduction Query Graph (backward) ===>")

            dg_reduction = DotGraph("reduction")
            dg_reduction += dg_reduc_setup + dg_reduc_query
            if verbose:
                print("<=== Reduction Graph ===>")
                print(dg_reduction)
                print("<=== Reduction Graph ===>")


            reductionData['reductionGraph'] = dg_reduction

        # TODO: expand search to encrypt and potentially setup
        pairingSearch += [stmtS, stmtQ] # aka start with decrypt.
                
        info[curveID] = options['secparam']
        info[dropFirstKeyword] = options[dropFirstKeyword]
        gen = Generators(info)
        # JAA: commented out for benchmarking    
        #print("List of generators for scheme")
        # retrieve the generators selected by the scheme
        # typically found in the setup routine in most cases.
        # extract the generators from the setup and keygen routine for later use
        if hasattr(cm, 'reducSetupFuncName'):
            gen.extractGens(stmtS, typesS)
        if hasattr(cm, 'reducQueryFuncName'):
            gen.extractGens(stmtQ, typesQ)
        else:
            sys.exit("Assumption failed: setup not defined for this function. Where to extract generators?")
        generators = gen.getGens()
        # JAA: commented out for benchmarking    
        #print("Generators extracted: ", generators)


    # need a Visitor class to build these variables  
    # TODO: expand to other parts of algorithm including setup, keygen, encrypt
    # Visits each pairing computation in the SDL and
    # extracts the inputs. This is the beginning of the
    # analysis of these variables as the SDL is converted into
    # an asymmetric scheme.
    hashVarList = []
    pair_vars_G1_lhs = [] 
    pair_vars_G1_rhs = []    
    gpv = GetPairingVariables(pair_vars_G1_lhs, pair_vars_G1_rhs)
    gpv.setDepListData( depListData )
    for eachStmt in pairingSearch: # loop through each pairing statement
        lines = eachStmt.keys() # for each line, do the following
        for i in lines:
            if type(eachStmt[i]) == sdl.VarInfo: # make sure we have the Var Object
                # assert that the statement contains a pairing computation
                gpv.setFuncName( eachStmt[i].getFuncName() )
                if HasPairings(eachStmt[i].getAssignNode()):
                    path_applied = []
                    # split pairings if necessary so that we don't influence
                    # the solve in anyway. We can later recombine these during
                    # post processing of the SDL
                    eachStmt[i].assignNode = SplitPairings(eachStmt[i].getAssignNode(), path_applied)
                    # JAA: commented out for benchmarking                    
                    #if len(path_applied) > 0: print("Split Pairings: ", eachStmt[i].getAssignNode())
                    if info['verbose']: print("Each: ", eachStmt[i].getAssignNode())
                    #print(eachStmt[i].assignNode)
                    sdl.ASTVisitor( gpv ).preorder( eachStmt[i].getAssignNode() )
                elif eachStmt[i].getHashArgsInAssignNode(): 
                    # in case there's a hashed value...build up list and check later to see if it appears
                    # in pairing variable list
                    hashVarList.append(str(eachStmt[i].getAssignVar()))
                else:
                    continue # not interested
                
    # constraint list narrows the solutions that
    # we care about
    constraintList = []
    # for example, include any hashed values that show up in a pairing by default
    for i in hashVarList:
        if i in pair_vars_G1_lhs or i in pair_vars_G1_rhs:
            constraintList.append(i)
    # JAA: commented out for benchmarking            
    # for each pairing variable, we construct a dependency graph all the way back to
    # the generators used. The input of assignTraceback consists of the list of SDL statements,
    # generators from setup, type info, and the pairing variables.
    # We do this analysis for both sides
    info[ 'G1_lhs' ] = (pair_vars_G1_lhs, assignTraceback(assignInfo_reduction, generators, varTypes, pair_vars_G1_lhs, constraintList))
    info[ 'G1_rhs' ] = (pair_vars_G1_rhs, assignTraceback(assignInfo_reduction, generators, varTypes, pair_vars_G1_rhs, constraintList))

    depList = {}
    depListUnaltered = {}

    if cm.schemeType == PKENC:
        for i in [depListS, depListQ, depListC]:
            for (key, val) in i.items():
                if(not(len(val) == 0) and not(key == 'input') and
                   not(key == 'output') and not(key == cm.reducCiphertextVar) and
                   not(key == cm.reducQueriesSecVar) and not(key in cm.reducMasterPubVars) and
                   not(key in cm.reducMasterSecVars)):
                    if(key in reductionData['varmap']):
                        depList[reductionData['varmap'][key]] = val
                        depListUnaltered[key] = val
                    else:
                        depList[key] = val
                        depListUnaltered[key] = val
    elif cm.schemeType == PKSIG:
        for i in [depListS, depListQ]:
            for (key, val) in i.items():
                if(not(len(val) == 0) and not(key == 'input') and not(key == 'output') and not(key == cm.reducCiphertextVar) and not(key == cm.reducQueriesSecVar) and not(key in cm.reducMasterPubVars) and not(key in cm.reducMasterSecVars)):
                    if(key in reductionData['varmap']):
                        depList[reductionData['varmap'][key]] = val
                        depListUnaltered[key] = val
                    else:
                        depList[key] = val
                        depListUnaltered[key] = val

    info[ 'deps' ] = (depListUnaltered, assignTraceback(assignInfo_reduction, generators, varTypes, depListUnaltered, constraintList))

    prunedDeps = {}
    for (key, val) in info['deps'][1].items():
        if(not(len(val) == 0)):
            prunedDeps[key] = val

    the_map = gpv.pairing_map

    reductionData['info'] = info
    reductionData['depList'] = depList
    reductionData['deps'] = info['deps']
    reductionData['prunedMap'] = prunedDeps

    reductionData['G1_lhs'] = info['G1_lhs']
    reductionData['G1_rhs'] = info['G1_rhs']

    reductionData['the_map'] = the_map

    reductionData['options'] = options

    reductionData['varTypes'] = varTypes

    #prune varTypes to remove ZR that we don't care about
    additionalDeps = dict(list(reductionData['info']['deps'][0].items()))
    items = []
    newlist = []
    newDeps = {}
    for (key,val) in additionalDeps.items():
        #items = list(additionalDeps[key])
        newlist = []
        for j in val:
            if((sdl.getVarTypeFromVarName(j, None, True) == types.G1) or (sdl.getVarTypeFromVarName(j, None, True) == types.G2)):
                newlist.append(j)
        if(not(len(set(newlist)) == 0)):
            if(key in reductionData['varmap']):
                newDeps[reductionData['varmap'][key]] = set(newlist)
            else:
                newDeps[key] = set(newlist)
            #newDeps[key] = set(newlist)
    reductionData['newDeps'] = newDeps

    reductionData['options']['type'] = "reduction"

    reductionData['reductionFile'] = reduction_file

    if cm.schemeType == PKENC and not cm.single_reduction:
        if hasattr(cm, 'graphit') and cm.graphit:
            exclude_list = [cm.reducQueriesSecVar] + cm.reducMasterPubVars + cm.reducMasterSecVars

            dg_reduc_setup = generateGraphForward(cm.reducSetupFuncName, (stmtS, typesS, infListNoExpS))
            dg_reduc_setup.adjustByMap(reductionData.get('varmap'))
            # process the query
            dg_reduc_query = generateGraph(cm.reducQueryFuncName, (typesQ, depListNoExpQ), types.G1, varTypes) #, stmts=stmtQ, infListNoExp=infListNoExpQ)
            dg_reduc_query.adjustByMap(reductionData.get('varmap'))

            try:
                newVarType = dict(typesS)
                newVarType.update(typesQ)
                # special variables that we don't want in the graph
                dg_reduc_query_forward = generateGraphForward(cm.reducQueryFuncName, (stmtQ, newVarType, infListNoExpQ), exclude=exclude_list)
                dg_reduc_query_forward.adjustByMap(reductionData.get('varmap'))
                # combine with backward analysis
                dg_reduc_query += dg_reduc_query_forward
            except Exception as e:
                print("EXCEPTION: ", cm.reducQueryFuncName, " forward tracing failed!")
                print(e.traceback())

            dg_reduc_chall = generateGraph(cm.reducChallengeFuncName, (typesC, depListNoExpC), types.G1, varTypes)
            dg_reduc_chall.adjustByMap(reductionData.get('varmap'))

            try:
                newVarType.update(typesC)
                dg_reduc_chall_forward = generateGraphForward(cm.reducChallengeFuncName, (stmtC, newVarType, infListNoExpC), exclude=exclude_list)
                dg_reduc_chall_forward.adjustByMap(reductionData.get('varmap'))
                # combine with backward analysis
                dg_reduc_chall += dg_reduc_chall_forward
            except Exception as e:
                print("EXCEPTION: ", cm.reducChallengeFuncName, " forward tracing failed!")
                print(e.traceback())


            if verbose:
                print("<=== Reduction Setup Graph ===>")
                print(dg_reduc_setup)
                print("<=== Reduction Setup Graph ===>")

                print("<=== Reduction Query Graph ===>")
                print(dg_reduc_query)
                print("<=== Reduction Query Graph ===>")

                print("<=== Reduction Challenge Graph ===>")
                print(dg_reduc_chall)
                print("<=== Reduction Challenge Graph ===>")

            dg_reduction = DotGraph("reduction")
            dg_reduction += dg_reduc_setup + dg_reduc_query + dg_reduc_chall
            if verbose:
                print("<=== Reduction Graph ===>")
                print(dg_reduction)
                print("<=== Reduction Graph ===>")

            reductionData['reductionGraph'] = dg_reduction


    #if hasattr(cm, "assumption_reduction_map"):
    #    reductionData['assumption'] = cm.assumption_reduction_map[reduction_name]
    #else:
    #    reductionData['assumption'] = ""

    return reductionData

def configAutoGroup(dest_path, sdl_file, config_file, output_file, verbose, benchmarkOpt, estimateOpt, shortOpt, run_auto_group):
    runningTime = 0

    # get full path (assuming not provided)
    full_config_file = os.path.abspath(config_file)
    pkg_name = os.path.basename(full_config_file)

    try:
        cm = imp.load_source(pkg_name, full_config_file)
    except:
        sys.exit("Missing config file: %s" % full_config_file)
    #check if gen visual dep graph
    if hasattr(cm, "graphit"):
        graphit = cm.graphit
    else:
        graphit = False

    # disable splitting of pk into spk/vpk
    cm.enablePKprune = False
    if shortOpt:
        # overrides the one in the cm
        cm.short = shortOpt
        if cm.short not in SHORT_OPTIONS:
            sys.exit("You specified an invalid option.\nValid ones: " + str(SHORT_OPTIONS))
        else:
            print("Running with short = ", cm.short)


    #parse assumption arguments
    if not hasattr(cm, "assumption") or run_auto_group:
        print("No assumption or specifically running the original AutoGroup")
        #sys.exit("configAutoGroup: need to set 'assumption' in config.") #TODO: add back in when finished and remove else

        # setup sdl parser configs
        sdl.masterPubVars = cm.masterPubVars
        sdl.masterSecVars = cm.masterSecVars
        if not hasattr(cm, "schemeType"):
            sys.exit("configAutoGroup: need to set 'schemeType' in config.")
        
        if cm.schemeType == PKENC and getattr(cm, functionOrder, None) == None:
            funcOrder = [cm.setupFuncName, cm.keygenFuncName, cm.encryptFuncName, cm.decryptFuncName]
            setattr(cm, functionOrder, funcOrder)
        elif cm.schemeType == PKSIG and getattr(cm, functionOrder, None) == None:
            if(hasattr(cm, "setupFuncName")):
                funcOrder = [cm.setupFuncName, cm.keygenFuncName, cm.signFuncName, cm.verifyFuncName]
            else:
                funcOrder = [cm.keygenFuncName, cm.signFuncName, cm.verifyFuncName]
            setattr(cm, functionOrder, funcOrder)

        print("function order: ", cm.functionOrder)
        
        if cm.schemeType == PKENC:
            for i in encConfigParams:
                if not hasattr(cm, i):
                    errorOut(i)
        elif cm.schemeType == PKSIG:
            for i in sigConfigParams:
                if not hasattr(cm, i):
                    errorOut(i)
        
        if not hasattr(cm, "secparam"):
            secparam = "BN256" # default pairing curve for now
        else:
            # need to check this against possible curve types
            secparam = cm.secparam
        
        dropFirst = None
        if hasattr(cm, "dropFirst"):
            dropFirst = cm.dropFirst
        
        options = {'secparam':secparam, 'userFuncList':[], 'computeSize':estimateOpt, 'dropFirst':dropFirst, 'path':dest_path, 'graphit':graphit}
        cm.forAutoGroupPlus = False

        startTime = time.clock()
        outfile_scheme = runAutoGroupOld(sdl_file, cm, options, verbose)
        endTime = time.clock()
        if benchmarkOpt: 
            runningTime += (endTime - startTime) * 1000
            print("running time: ", str(runningTime) + "ms")
            os.system("echo '%s' >> %s" % (runningTime, output_file))
    
        new_input_sdl  = outfile_scheme
        new_output_sdl = output_file
        # JAA: commented out for benchmark purposes
        if verbose:
            print("Codegen Input: ", new_input_sdl)
            print("Codegen Output: ", new_output_sdl)
            print("User defined funcs: ", options['userFuncList'])
        if not benchmarkOpt:
            # generate the source code in the target path
            codegen_CPP.codegen_CPP_main(dest_path + new_input_sdl, dest_path + new_output_sdl + ".cpp", options['userFuncList'])
            codegen_PY.codegen_PY_main(dest_path + new_input_sdl, dest_path + new_output_sdl + ".py", new_output_sdl + "User.py")
        return
    else:
        #assumptionData = []
        assumptionData = {}
        for i in cm.assumption:
            assumptionFile = os.path.dirname(full_config_file) + "/" + i + ".sdl" #TODO: how to determine location of assumption SDL file??

            startTime = time.clock()
            assumptionFileParseRun = parseAssumptionFile(cm, assumptionFile, verbose, benchmarkOpt, estimateOpt)
            endTime = time.clock()

            #assumptionData.append(assumptionFileParseRun)
            assumptionData[i] = assumptionFileParseRun

            if benchmarkOpt: 
                runningTime += (endTime - startTime) * 1000
                print("running time: ", str(runningTime) + "ms")

        setattr(cm, functionOrder, None)

        #parse reduction arguments
        if not hasattr(cm, "reduction"):
            print("No reduction specified")
            sys.exit("configAutoGroup: assumption set; need to set 'reduction' in config.") #TODO: add back in when finished and remove else
        else:
            print(cm.reduction)
            if len(cm.reduction) == 1:
                cm.single_reduction = True
            else:
                cm.single_reduction = False
            #reductionData = []
            reductionData = {}
            for i in cm.reduction:
                reductionFile = os.path.dirname(full_config_file) + "/" + i + ".sdl" #TODO: how to determine location of reduction SDL file??

                startTime = time.clock()
                reductionFileParseRun = parseReductionFile(cm, reductionFile, verbose, benchmarkOpt, estimateOpt)
                endTime = time.clock()

                #reductionData.append(reductionFileParseRun)
                reductionData[i] = reductionFileParseRun

                if benchmarkOpt: 
                    runningTime += (endTime - startTime) * 1000
                    print("running time: ", str(runningTime) + "ms")

            setattr(cm, functionOrder, None)

            # setup sdl parser configs
            sdl.masterPubVars = cm.masterPubVars
            sdl.masterSecVars = cm.masterSecVars
            if not hasattr(cm, "schemeType"):
                sys.exit("configAutoGroup: need to set 'schemeType' in config.")
            
            if cm.schemeType == PKENC and getattr(cm, functionOrder, None) == None:
                funcOrder = [cm.setupFuncName, cm.keygenFuncName, cm.encryptFuncName, cm.decryptFuncName]
                setattr(cm, functionOrder, funcOrder)
            elif cm.schemeType == PKSIG and getattr(cm, functionOrder, None) == None:
                if(hasattr(cm, "setupFuncName")):
                    funcOrder = [cm.setupFuncName, cm.keygenFuncName, cm.signFuncName, cm.verifyFuncName]
                else:
                    funcOrder = [cm.keygenFuncName, cm.signFuncName, cm.verifyFuncName]
                setattr(cm, functionOrder, funcOrder)

            if cm.schemeType == PKENC:
                for i in encConfigParams:
                    if not hasattr(cm, i):
                        errorOut(i)
            elif cm.schemeType == PKSIG:
                for i in sigConfigParams:
                    if not hasattr(cm, i):
                        errorOut(i)
            
            if not hasattr(cm, "secparam"):
                secparam = "BN256" # default pairing curve for now
            else:
                secparam = cm.secparam
            
            dropFirst = None
            if hasattr(cm, "dropFirst"):
                dropFirst = cm.dropFirst
            
            options = {'secparam':secparam, 'userFuncList':[], 'computeSize':estimateOpt, 'dropFirst':dropFirst, 'path':dest_path, 'graphit':graphit}
            cm.forAutoGroupPlus = True

            startTime = time.clock()
            (outfile_scheme, outfile_assump) = runAutoGroup(sdl_file, cm, options, verbose, assumptionData, reductionData)
            endTime = time.clock()
            if benchmarkOpt: 
                runningTime += (endTime - startTime) * 1000
                print("running time: ", str(runningTime) + "ms")
                os.system("echo '%s' >> %s" % (runningTime, output_file))
        
            new_input_sdl  = outfile_scheme
            new_output_sdl = output_file
            # JAA: commented out for benchmark purposes
            if verbose:
                print("Codegen Input: ", new_input_sdl)
                print("Codegen Output: ", new_output_sdl)
                print("User defined funcs: ", options['userFuncList'])
            if not benchmarkOpt:
                codegen_CPP.codegen_CPP_main(new_input_sdl, dest_path + new_output_sdl + ".cpp", options['userFuncList'])
                codegen_PY.codegen_PY_main(new_input_sdl, dest_path + new_output_sdl + ".py", new_output_sdl + "User.py")
            return

# run AutoGroup with the designated options
configAutoGroup(dest_path, sdl_file, config_file, output_file, verbose, benchmarkOpt, estimateSize, short_option, run_auto_group)
