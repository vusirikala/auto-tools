#!/bin/bash

set -x
# all the asymmetric tests

python genMakefile.py ./config.mk MakefileCL "FOO=1" TestCLorig.cpp benchCLorig.cpp

#python genMakefile.py ./config.mk MakefileBB "FOO=1" TestBBorig.cpp benchBBorig.cpp

#python genMakefile.py ./config.mk MakefileWAT "FOO=1" TestWaters05orig.cpp benchWATorig.cpp

#python genMakefile.py ./config.mk MakefileDSE "FOO=1" TestDSESigorig.cpp benchDSEorig.cpp

#python genMakefile.py ./config.mk MakefileACDK "FOO=1" TestACDKorig.cpp benchACDKorig.cpp

./TestCLorig 100 100 fixed

#./TestBBorig 100 100 fixed

#./TestWaters05orig 100 128 fixed

#./TestDSESigorig 100 100 fixed

#./TestACDKorig 100 100 fixed

set +x
