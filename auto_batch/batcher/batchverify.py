# Entry point to executing the batcher algorithm. It takes in an input bv file
# which describes the verification equation, variable types, components of the public, signature
# and message. Finally, an optional transform section to describe the specific order in which
# to apply the techniques 2, 3a, 3b and 4.

from batchtechniques import *
from batchproof import *
from batchorder import BatchOrder

try:
    #import benchmarks
    import miraclbench
    curve = miraclbench.benchmarks
    curve_key = 'mnt160'
except:
    print("Could not find the 'benchmarks' file that has measurement results! Generate and re-run.")
    exit(0)

debug = False

def countInstances(equation):
    Instfind = ExpInstanceFinder()
    ASTVisitor(Instfind).preorder(equation)
    print("Instances found =>", Instfind.instance, "\n")
    return Instfind.instance

def isOptimized(data):
    # check for counts greater than 1
    for i in data.keys():
        for j in data[i]:
            # if condition is true, then more optimizations are possible
            # effectively, a ^ b occurs more than once
            if data[i][j] > 1: return False
    return True

def checkForSigs(node):
    if node == None: return None
    if Type(node) == ops.HASH:
        return checkForSigs(node.left)
    elif Type(node) == ops.ATTR:
        if node.attr_index and 'z' in node.attr_index: return True
        else: return False
    else: # not sure about this but will see
        result = checkForSigs(node.left)
        if result: return result
        result = checkForSigs(node.right)
        return result

def benchIndivVerification(N, equation, const, vars, precompute, _verbose):
    rop_ind = RecordOperations(vars)
    # add attrIndex to non constants
    ASTVisitor(ASTAddIndex(const, vars)).preorder(equation)
    print("Final indiv eq:", equation, "\n")
    if _verbose:
        print("<====\tINDIVIDUAL\t====>")
        print("vars =>", vars)
        print("Equation =>", equation)
    data = {'key':['N'], 'N': N }

    rop_ind.visit(verify.right, data)
    if _verbose: print("<===\tOperations count\t===>")
    for i in precompute.keys():
            # if a str, then was precompute introduced programmatically and should skip for individual verification case. 
            if checkForSigs(precompute[i]): data = {'key':['N'], 'N': N }
            else: data = {}            
            rop_ind.visit(precompute[i], data)
            if _verbose: print("Precompute:", i, ":=", precompute[i])
    if _verbose:
        print_results(rop_ind.ops)
    return calculate_times(rop_ind.ops, curve['mnt160'], N)
    

def benchBatchVerification(N, equation, const, vars, precompute, _verbose):
    rop_batch = RecordOperations(vars)
    rop_batch.visit(equation, {})
    if _verbose:
        print("<====\tBATCH\t====>")
        print("Equation =>", equation)
        print("<===\tOperations count\t===>")
    for i in precompute.keys():
        if type(i) != str:
            if checkForSigs(precompute[i]): data = {'key':['N'], 'N': N }
            else: data = {}
            rop_batch.visit(precompute[i], data)
            if _verbose: print("Precompute:", i, ":=", precompute[i])
        else:
            if i == 'delta': # estimate cost of random small exponents
                rop_batch.ops['prng'] += N
                if _verbose: print("Precompute:", i, ":=", precompute[i])
            else:  # estimate cost of some precomputations
                bp = BatchParser()
                index = BinaryNode( i )
                if 'j' in index.attr_index:
                    compute = bp.parse( "for{z:=1, N} do " + precompute[i] )
                    rop_batch.visit(compute, {})
                    if _verbose: print("Precompute:", i, ":=", compute)
                else:
                    if _verbose: print("TODO: need to account for this: ", i, ":=", precompute[i])
    if _verbose:
        print_results(rop_batch.ops)
    return calculate_times(rop_batch.ops, curve['mnt160'], N)

def proofHeader(lcg, title, const, sigs, indiv_eq, batch_eq):
    const_str = ""; sig_str = ""
    for i in const:
        const_str += lcg.getLatexVersion(i) + ","
    const_str = const_str[:len(const_str)-1]
    for i in sigs:
        sig_str += lcg.getLatexVersion(i) + ","
    sig_str = sig_str[:len(sig_str)-1]
    result = header % (title, const_str, sig_str, indiv_eq, batch_eq)
    #print("header =>", result)
    return result

def proofBody(step, data):
    pre_eq = data.get('preq')
    cur_eq = data['eq']
    if pre_eq != None:
        result_eq = pre_eq + cur_eq
    else: result_eq = cur_eq    
    result = basic_step % (step, data['msg'], result_eq)
    #print('[STEP', step, ']: ', result)
    return result

def writeConfig(lcg, latex_file, lcg_data, const, vars, sigs):
    f = open('verification_gen' + latex_file + '.tex', 'w')
    title = latex_file.upper()
    outputStr = proofHeader(lcg, title, const, sigs, lcg_data[0]['eq'], lcg_data[0]['batch'])
    for i in lcg_data.keys():
        if i != 0:
            outputStr += proofBody(i, lcg_data[i])
    outputStr += footer
    f.write(outputStr)
    f.close()
    return
    
if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("%s [ batch-input.bv ] -b -c -p" % sys.argv[0])
        print("-b : estimate threshold for a given signature scheme with 1 to N signatures.")
        print("-c : generate the output for the code generator (temporary).")
        print("-d : check for further precomputations in final batch equation.")
        print("-p : generate the proof for the signature scheme.")
        print("-s : select strategy for the ordering of techniques. Options: basic, score, what else?")
        exit(-1)
    # main for batch input parser    
    try:
        file = sys.argv[1]
        print(sys.argv[1:])
        ast_struct = parseFile(file)
        THRESHOLD_FLAG = CODEGEN_FLAG = PROOFGEN_FLAG = PRECOMP_CHECK = VERBOSE = CHOOSE_STRATEGY = False # initialization
        for i in sys.argv:
            if i == "-b": THRESHOLD_FLAG = True
            elif i == "-c": CODEGEN_FLAG = True
            elif i == "-v": VERBOSE = True
            elif i == "-p": PROOFGEN_FLAG = True
            elif i == "-d": PRECOMP_CHECK = True
            elif i == "-s": CHOOSE_STRATEGY = True
    except:
        print("An error occured while processing batch inputs.")
        exit(-1)
    const, types = ast_struct[ CONST ], ast_struct[ TYPE ]
    latex_subs = ast_struct[ LATEX ]
    (indiv_precompute, batch_precompute) = ast_struct[ PRECOMP ]
    batch_precompute[ "delta" ] = "for{z := 1, N} do prng_z"
    
    algorithm = ast_struct [ TRANSFORM ]
    FIND_ORDER     = False
    if not algorithm: FIND_ORDER = True #algorithm = ['2', '3'];  

    verify, N = None, None
    setting = {}
    metadata = {}
    for n in ast_struct[ OTHER ]:
        if str(n.left) == 'verify':
            verify = n
        elif str(n.left) == 'N':
            N = int(str(n.right))
            metadata['N'] = str(n.right)
        elif str(n.left) in [SIGNATURE, PUBLIC, MESSAGE]:
            setting[ str(n.left) ] = str(n.right)
        else:
            metadata[ str(n.left) ] = str(n.right)
    
    # process settings
    sig_vars, pub_vars, msg_vars = ast_struct[ SIGNATURE ], ast_struct[ PUBLIC ], ast_struct[ MESSAGE ]
    batch_count = {} # F = more than one, T = only one exists
    MSG_set = setting.get(MESSAGE)
    PUB_set = setting.get(PUBLIC)
    SIG_set = setting.get(SIGNATURE)
    if MSG_set == SAME:
        batch_count[ MESSAGE ] = SAME 
    elif MSG_set in metadata.keys():
        checkDotProd = CheckExistingDotProduct(MSG_set)
        ASTVisitor(checkDotProd).preorder(verify.right)
        if not checkDotProd.applied:
            batch_count[ MESSAGE ] = MSG_set
        else:
            batch_count[ MESSAGE ] = None
    else:
        print("variable not defined but referenced: ", MSG_set)
    
    # check public key setting (can either be many keys or just one single key)
    if PUB_set == SAME:
        batch_count[ PUBLIC ] = SAME 
    elif PUB_set in metadata.keys():
        checkDotProd = CheckExistingDotProduct(PUB_set)
        ASTVisitor(checkDotProd).preorder(verify.right)
        if not checkDotProd.applied:
            batch_count[ PUBLIC ] = PUB_set
        else:
            batch_count[ PUBLIC ] = None
        
    else:
        print("variable not defined but referenced: ", PUB_set)
    
    if SIG_set in metadata.keys():
        batch_count[ SIGNATURE ] = SIG_set
    else:
        print("variable not defined but referenced: ", SIG_set)    
    
    if VERBOSE: print("setting: ", batch_count)
    
#    exit(0)
    vars = types
    vars['N'] = N
    vars.update(metadata)
    print("variables =>", vars)
    print("metadata =>", metadata)

    if PROOFGEN_FLAG:
        lcg_data = {}
        lcg_steps = 0
        lcg = LatexCodeGenerator(const, vars, latex_subs)


    print("\nVERIFY EQUATION =>", verify)
    if PROOFGEN_FLAG: lcg_data[ lcg_steps ] = { 'msg':'Equation', 'eq': lcg.print_statement(verify.right) }; lcg_steps += 1
    verify2 = BinaryNode.copy(verify)
#    ASTVisitor(CombineVerifyEq(const, vars)).preorder(verify2.right)
    ASTVisitor(CVForMultiSigner(vars, sig_vars, pub_vars, msg_vars, batch_count)).preorder(verify2.right)
    if PROOFGEN_FLAG: lcg_data[ lcg_steps ] = { 'msg':'Combined Equation', 'eq':lcg.print_statement(verify2.right) }; lcg_steps += 1
    ASTVisitor(SimplifyDotProducts()).preorder(verify2.right)

    print("\nStage A: Combined Equation =>", verify2)
    ASTVisitor(SmallExponent(const, vars)).preorder(verify2.right)
    print("\nStage B: Small Exp Test =>", verify2, "\n")
    if PROOFGEN_FLAG: lcg_data[ lcg_steps ] = { 'msg':'Apply the small exponents test, using exponents $\delta_1, \dots \delta_\\numsigs \in_R \Zq$', 
                                               'eq':lcg.print_statement(verify2.right), 'preq':small_exp_label }; lcg_steps += 1


    # figure out order automatically (if not specified in bv file)
    if FIND_ORDER:
        result = BatchOrder(const, types, vars, BinaryNode.copy(verify2.right)).strategy()
        algorithm = [str(x) for x in result]
        print("found batch algorithm =>", algorithm)

    techniques = {'2':Technique2, '3':Technique3, '4':Technique4, '5':SimplifyDotProducts, '6':PairInstanceFinder }

    for option in algorithm:
        if option == '5':
            option_str = "Simplifying =>"
            Tech = techniques[option]()
        elif option == '6':
            option_str = "Combine Pairings:"
            Tech = techniques[option]()            
        elif option in techniques.keys():
            option_str = "Applying technique " + option
            Tech = techniques[option](const, vars, metadata)
        else:
            print("Unrecognized technique selection.")
            continue
        ASTVisitor(Tech).preorder(verify2.right)
        if option == '6':
            Tech.makeSubstitution(verify2.right)
        print(Tech.rule, "\n")
        print(option_str, ":",verify2.right, "\n")
        if PROOFGEN_FLAG:
            lcg_data[ lcg_steps ] = { 'msg':Tech.rule, 'eq': lcg.print_statement(verify2.right) }
            lcg_steps += 1

#    exit(0)
    
    if PROOFGEN_FLAG:
        lcg_data[ lcg_steps-1 ]['preq'] = final_batch_eq
        lcg_data[0]['batch'] = lcg_data[ lcg_steps-1 ]['eq']
        
    if PRECOMP_CHECK:
        countDict = countInstances(verify2) 
        if not isOptimized(countDict):
            ASTVisitor(SubstituteExps(countDict, batch_precompute, vars)).preorder(verify2.right)
            print("Final batch eq:", verify2.right)
        else:
            print("Final batch eq:", verify2.right)

    # START BENCHMARK : THRESHOLD ESTIMATOR
    if THRESHOLD_FLAG:
        print("<== Running threshold estimator ==>")
        (indiv_msmt, indiv_avg_msmt) = benchIndivVerification(N, verify.right, const, vars, indiv_precompute, VERBOSE)
        print("Result N =",N, ":", indiv_avg_msmt)

        outfile = file.split('.')[0]
        indiv, batch = outfile + "_indiv.dat", outfile + "_batch.dat"
    
        output_indiv = open(indiv, 'w'); output_batch = open(batch, 'w')
        threshold = -1
        for i in range(1, N+1):
            vars['N'] = i
            (batch_msmt, batch_avg_msmt) = benchBatchVerification(i, verify2.right, const, vars, batch_precompute, VERBOSE)
            output_indiv.write(str(i) + " " + str(indiv_avg_msmt) + "\n")
            output_batch.write(str(i) + " " + str(batch_avg_msmt) + "\n")
            if batch_avg_msmt <= indiv_avg_msmt and threshold == -1: threshold = i 
        output_indiv.close(); output_batch.close()
        print("Result N =",N, ":", batch_avg_msmt)
        print("Threshold: ", threshold)
    # STOP BENCHMARK : THRESHOLD ESTIMATOR 
    # TODO: check avg for when batch is more efficient than 
    if CODEGEN_FLAG:
        print("Final batch eq:", verify2.right)
        subProds = SubstituteSigDotProds(vars, 'z', 'N')
        ASTVisitor(subProds).preorder(verify2.right)
        # print("Dot prod =>", subProds.dotprod)
        # need to check for presence of other variables
        key = None
        for i in metadata.keys():
            if i != 'N': key = i
        subProds1 = SubstituteSigDotProds(vars, 'y', key)
        subProds1.setState(subProds.cnt)
        ASTVisitor(subProds1).preorder(verify2.right)
    
        print("<====\tPREP FOR CODE GEN\t====>")
        print("\nFinal version =>", verify2.right, "\n")
        for i in subProds.dotprod['list']:
            print("Compute: ", i,":=", subProds.dotprod['dict'][i])    
#    print("Dot prod =>", subProds1.dotprod)
        for i in subProds1.dotprod['list']:
            print("Compute: ", i,":=", subProds1.dotprod['dict'][i])
        for i in batch_precompute.keys():
            print("Precompute:", i, ":=", batch_precompute[i])
        for i in subProds.dotprod['list']:
            print(i,":=", subProds.dotprod['types'][i])    

    if PROOFGEN_FLAG:
        print("Generated the proof for the given signature scheme.")
        latex_file = metadata['name'].upper()
        writeConfig(lcg, latex_file, lcg_data, const, vars, sigs)
#        lcg = LatexCodeGenerator(const, vars)
#        equation = lcg.print_statement(verify2.right)
#        print("Latex Equation: ", equation)
        
        
