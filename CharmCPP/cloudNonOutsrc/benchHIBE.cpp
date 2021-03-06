#include "TestHIBE.h"
#include <fstream>

string getID(int len)
{
	string alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
	string id = "";
	int val, alpha_len = alphabet.size();
	for(int i = 0; i < len; i++)
	{
		val = (int) (rand() % alpha_len);
		id +=  alphabet[val];
	}
	cout << "Rand selected ID: '" << id << "'" << endl;
	return id;
}

void benchmarkHIBE(Hibe & hibe, ofstream & outfile1, ofstream & outfile2, int ID_string_len, int iterationCount, CharmListStr & keygenResults, CharmListStr & decryptResults)
{
	int l = 5;
	int z = 32;
	Benchmark benchT, benchD, benchK;
    CharmList mk, mpk, pk, sk, sk2, ct;
    GT M, newM;
    ZR uf0;
    string id = getID(ID_string_len); // "somebody@example.com"; // make this longer?
    double de_in_ms, kg_in_ms;

	hibe.setup(l, z, mpk, mk);
	for(int i = 0; i < iterationCount; i++) {
		benchK.start();
		hibe.keygen(mpk, mk, id, pk, sk2);
		benchK.stop();
		kg_in_ms = benchK.computeTimeInMilliseconds();
	}
	cout << "Keygen avg: " << benchK.getAverage() << " ms" << endl;
    stringstream s1;
	s1 << ID_string_len << " " << benchK.getAverage() << endl;
	outfile1 << s1.str();
    keygenResults[ID_string_len] = benchK.getRawResultString();

	hibe.keygen(mpk, mk, id, pk, sk);
    M = hibe.group.random(GT_t);
    hibe.encrypt(mpk, pk, M, ct);

    stringstream s2;

    //cout << "ct =\n" << ct << endl;
	for(int i = 0; i < iterationCount; i++) {
		benchD.start();
		hibe.decrypt(pk, sk, ct, newM);
		benchD.stop();
		de_in_ms = benchD.computeTimeInMilliseconds();
	}

	cout << "Decrypt avg: " << benchD.getAverage() << " ms" << endl;
	s2 << iterationCount << " " << benchD.getAverage() << endl;
	outfile2 << s2.str();
	decryptResults[ID_string_len] = benchD.getRawResultString();

    //cout << convert_str(M) << endl;
    //cout << convert_str(newM) << endl;
    if(M == newM) {
      cout << "Successful Decryption!" << endl;
    }
    else {
      cout << "FAILED Decryption." << endl;
    }
    return;
}

int main(int argc, const char *argv[])
{
	string FIXED = "fixed", RANGE = "range";
	if(argc != 4) { cout << "Usage " << argv[0] << ": [ iterationCount => 10 ] [ ID-string => 100 ] [ 'fixed' or 'range' ]" << endl; return -1; }

	int iterationCount = atoi( argv[1] );
	int ID_string_len = atoi( argv[2] );
	string fixOrRange = string(argv[3]);
	cout << "iterationCount: " << iterationCount << endl;
	cout << "ID-string: " << ID_string_len << endl;
	cout << "measurement: " << fixOrRange << endl;

	srand(time(NULL));
	Hibe hibe;
	string filename = string(argv[0]);
	stringstream s3, s4;
	ofstream outfile1, outfile2, outfile3, outfile4;
	string f1 = filename + "_keygen.dat";
	string f2 = filename + "_decrypt.dat";
	string f3 = filename + "_keygen_raw.txt";
	string f4 = filename + "_decrypt_raw.txt";
	outfile1.open(f1.c_str());
	outfile2.open(f2.c_str());
	outfile3.open(f3.c_str());
	outfile4.open(f4.c_str());

	CharmListStr keygenResults, decryptResults;
	if(isEqual(fixOrRange, RANGE)) {
		for(int i = 2; i <= ID_string_len; i++) {
			benchmarkHIBE(hibe, outfile1, outfile2, i, iterationCount, keygenResults, decryptResults);
		}
		s4 << decryptResults << endl;
	}
	else if(isEqual(fixOrRange, FIXED)) {
		benchmarkHIBE(hibe, outfile1, outfile2, ID_string_len, iterationCount, keygenResults, decryptResults);
		s3 << ID_string_len << " " << keygenResults[ID_string_len] << endl;
		s4 << ID_string_len << " " << decryptResults[ID_string_len] << endl;
	}
	else {
		cout << "invalid option." << endl;
		return -1;
	}

	outfile3 << s3.str();
	outfile4 << s4.str();
	outfile1.close();
	outfile2.close();
	outfile3.close();
	outfile4.close();
	return 0;
}
