from charm.toolbox.pairinggroup import *
from charm.core.math.integer import randomBits
import sys

paramList = ['BN256']
trials = 1
curve = {}
time_in_ms = 1000
Bits = 80 # security level for PRNG

def getGroupConst(groupStr):
    if(groupStr == 'ZR'):
        return ZR
    elif (groupStr == 'G1'):
        return G1
    elif (groupStr == 'G2'):
        return G2
    elif (groupStr == 'GT'):
        return GT
    else:
        return NULL

def mul_in_grp(group, grpChoice):
    assert group.InitBenchmark(), "failed to init benchmark"
    a, b = group.random(getGroupConst(grpChoice)), group.random(getGroupConst(grpChoice))

    group.StartBenchmark(["CpuTime"])
    for i in range(0, trials):
        c = a * b

    group.EndBenchmark()
    result = (group.GetBenchmark("CpuTime") / trials) * time_in_ms
    return result

def exp_in_grp(group, grpChoice):
    assert group.InitBenchmark(), "failed to init benchmark"
    g, a = group.random(getGroupConst(grpChoice)), group.random(ZR)
    g.initPP() 

    group.StartBenchmark(["CpuTime"])
    for i in range(0, trials):
        c = g ** (a * (i+1))

    group.EndBenchmark()
    result = (group.GetBenchmark("CpuTime") / trials) * time_in_ms
    del g
    return result

def hash_in_grp(group, grpChoice):
    assert group.InitBenchmark(), "failed to init benchmark"
    _hash = group.hash
    _grp = getGroupConst(grpChoice)
    m = "this is some message of a good length!!!" # 40 bytes
    group.StartBenchmark(["CpuTime"])
    for i in range(trials):
        res = _hash(m, _grp)
    group.EndBenchmark()
    result = (group.GetBenchmark("CpuTime") / trials) * time_in_ms
    return result

def prng_bits(group, bits=80):
    assert group.InitBenchmark(), "failed to init benchmark"
    group.StartBenchmark(["CpuTime"])
    for i in range(trials):
        a = group.init(ZR, randomBits(bits))
    group.EndBenchmark()
    result = (group.GetBenchmark("CpuTime") / trials) * time_in_ms
    return result

def bench(param):
    group = PairingGroup(param)

    assert group.InitBenchmark(), "failed to init benchmark"
    a, b = group.random(G1), group.random(G2)

    group.StartBenchmark(["CpuTime"])
    for i in range(0, trials):
        c = pair(a, b)
    group.EndBenchmark()

    curve[param]['pair'] = (group.GetBenchmark("CpuTime") / trials) * time_in_ms

    
    for i in ['G1', 'G2', 'GT']:
        curve[param]['mul'][i] = mul_in_grp(group, i)        
        curve[param]['exp'][i] = exp_in_grp(group, i)
    
    curve[param]['hash']['ZR'] = hash_in_grp(group, 'ZR')
    curve[param]['hash']['G1'] = hash_in_grp(group, 'G1')
    curve[param]['hash']['G2'] = curve[param]['hash']['GT'] = 0
    # how long it takes to generate integers of a certain number of bits
    curve[param]['prng'] = prng_bits(group)
    return 

def generateOutput(outputFile):
    file = open(outputFile, 'w')
    data = open(outputFile + ".py", 'w')
    
    dataStr = ""
    dataStr += "benchmarks = " + str(curve)
    data.write(dataStr)
    data.close()
    
    outputString = ""

    outputString += "\n<= Benchmark Results =>\n\n"
    outputString += "Raw Output:\n"
    outputString += str(curve)
    outputString += "\n\n"
    outputString += "Formatted Output:\n\n"

    for param in curve:
        outputString += "\t" + str(param) + "\n"
        for benchmark in curve[param]:
            if (benchmark == "pair"):
                outputString += "\t\tpair:  " + str(curve[param]['pair']) + " ms\n"
            elif (benchmark == "prng"):
                outputString += "\t\tprng of "+ str(Bits) + " bits:  " + str(curve[param]['prng']) + " ms\n"
            elif (benchmark == "hash"):
                outputString += "\t\t" + benchmark + ":\n"
                for i in ['ZR', 'G1']:
                    outputString += "\t\t\t" + i + ":  " + str(curve[param][benchmark][i]) + " ms\n"
            else:
                outputString += "\t\t" + benchmark + ":\n"
                for i in ['G1', 'G2', 'GT']:
                    outputString += "\t\t\t" + i + ":  " + str(curve[param][benchmark][i]) + " ms\n"
        outputString += "\n"

    outputString += "Done.\n"

    print(outputString)
    file.write(outputString)
    file.close()

if __name__ == "__main__":
    if ( (len(sys.argv) != 3) or (sys.argv[1] == "-help") or (sys.argv[1] == "--help") ):
        sys.exit("Usage:  python %s [number of trials] [output file]" % sys.argv[0])

    trials = int(sys.argv[1])
    outputFile = sys.argv[2]

    for paramEntry in paramList:
        grps = {'ZR':0.0, 'G1':0.0, 'G2':0.0, 'GT':0.0}
        curve[paramEntry] = {'pair':0.0, 'mul':grps.copy(), 
                             'exp':grps.copy(), 'hash':grps.copy(), 'prng':0.0 }

    for key in curve:
        bench(key)

    generateOutput(outputFile)
