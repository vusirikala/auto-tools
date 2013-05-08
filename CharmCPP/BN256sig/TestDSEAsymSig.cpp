#include "TestDSEAsymSig.h"

void Dse09sig::keygen(CharmList & sk, CharmList & spk, CharmList & vpk)
{
    G1 gG1;
    G2 gG2;
    ZR w;
    G1 wG1;
    ZR u;
    G1 uG1;
    ZR h;
    G1 hG1;
    ZR v;
    G1 vG1;
    G2 vG2;
    ZR v1;
    G1 v1G1;
    G2 v1G2;
    ZR v2;
    G1 v2G1;
    G2 v2G2;
    ZR a1;
    ZR a2;
    ZR b;
    ZR alpha;
    G1 gbG1;
    G2 gbG2;
    G1 ga1;
    G1 ga2;
    G2 gba1;
    G2 gba2;
    G1 tau1G1;
    G2 tau1G2;
    G1 tau2G1;
    G2 tau2G2;
    G1 tau1b;
    G1 tau2b;
    GT A = group.init(GT_t);
    G2 galpha;
    G2 galphaa1;
    gG1 = group.random(G1_t);
    gG2 = group.random(G2_t);
    w = group.random(ZR_t);
    wG1 = group.exp(gG1, w);
    u = group.random(ZR_t);
    uG1 = group.exp(gG1, u);
    h = group.random(ZR_t);
    hG1 = group.exp(gG1, h);
    v = group.random(ZR_t);
    vG1 = group.exp(gG1, v);
    vG2 = group.exp(gG2, v);
    v1 = group.random(ZR_t);
    v1G1 = group.exp(gG1, v1);
    v1G2 = group.exp(gG2, v1);
    v2 = group.random(ZR_t);
    v2G1 = group.exp(gG1, v2);
    v2G2 = group.exp(gG2, v2);
    a1 = group.random(ZR_t);
    a2 = group.random(ZR_t);
    b = group.random(ZR_t);
    alpha = group.random(ZR_t);
    gbG1 = group.exp(gG1, b);
    gbG2 = group.exp(gG2, b);
    ga1 = group.exp(gG1, a1);
    ga2 = group.exp(gG1, a2);
    gba1 = group.exp(gbG2, a1);
    gba2 = group.exp(gbG2, a2);
    tau1G1 = group.mul(vG1, group.exp(v1G1, a1));
    tau1G2 = group.mul(vG2, group.exp(v1G2, a1));
    tau2G1 = group.mul(vG1, group.exp(v2G1, a2));
    tau2G2 = group.mul(vG2, group.exp(v2G2, a2));
    tau1b = group.exp(tau1G1, b);
    tau2b = group.exp(tau2G1, b);
    A = group.exp(group.pair(gG1, gG2), group.mul(alpha, group.mul(a1, b)));
    galpha = group.exp(gG2, alpha);
    galphaa1 = group.exp(galpha, a1);
    spk.insert(0, A);
    spk.insert(1, gG1);
    spk.insert(2, gG2);
    spk.insert(3, gbG1);
    spk.insert(4, gbG2);
    spk.insert(5, hG1);
    spk.insert(6, tau1G1);
    spk.insert(7, tau2G1);
    spk.insert(8, uG1);
    spk.insert(9, wG1);
    vpk.insert(0, A);
    vpk.insert(1, gG2);
    vpk.insert(2, ga1);
    vpk.insert(3, ga2);
    vpk.insert(4, gbG1);
    vpk.insert(5, gba1);
    vpk.insert(6, gba2);
    vpk.insert(7, hG1);
    vpk.insert(8, tau1G2);
    vpk.insert(9, tau1b);
    vpk.insert(10, tau2G2);
    vpk.insert(11, tau2b);
    vpk.insert(12, wG1);
    sk.insert(0, galpha);
    sk.insert(1, galphaa1);
    sk.insert(2, vG1);
    sk.insert(3, vG2);
    sk.insert(4, v1G1);
    sk.insert(5, v1G2);
    sk.insert(6, v2G1);
    sk.insert(7, v2G2);
    sk.insert(8, alpha);
    return;
}

void Dse09sig::sign(CharmList & spk, CharmList & sk, string & m, CharmList & sig)
{
    GT A;
    G1 gG1;
    G2 gG2;
    G1 gbG1;
    G2 gbG2;
    G1 hG1;
    G1 tau1G1;
    G1 tau2G1;
    G1 uG1;
    G1 wG1;
    G2 galpha;
    G2 galphaa1;
    G1 vG1;
    G2 vG2;
    G1 v1G1;
    G2 v1G2;
    G1 v2G1;
    G2 v2G2;
    ZR alpha;
    ZR r1;
    ZR r2;
    ZR z1;
    ZR z2;
    ZR tagk;
    ZR r;
    ZR M;
    G2 S1;
    G1 S2;
    G2 S3;
    G1 S4;
    G2 S5;
    G1 S6;
    G2 S7;
    G1 SK;
    
    A = spk[0].getGT();
    gG1 = spk[1].getG1();
    gG2 = spk[2].getG2();
    gbG1 = spk[3].getG1();
    gbG2 = spk[4].getG2();
    hG1 = spk[5].getG1();
    tau1G1 = spk[6].getG1();
    tau2G1 = spk[7].getG1();
    uG1 = spk[8].getG1();
    wG1 = spk[9].getG1();
    
    galpha = sk[0].getG2();
    galphaa1 = sk[1].getG2();
    vG1 = sk[2].getG1();
    vG2 = sk[3].getG2();
    v1G1 = sk[4].getG1();
    v1G2 = sk[5].getG2();
    v2G1 = sk[6].getG1();
    v2G2 = sk[7].getG2();
    alpha = sk[8].getZR();
    r1 = group.random(ZR_t);
    r2 = group.random(ZR_t);
    z1 = group.random(ZR_t);
    z2 = group.random(ZR_t);
    tagk = group.random(ZR_t);
    r = group.add(r1, r2);
    M = group.hashListToZR(m);
    S1 = group.mul(galphaa1, group.exp(vG2, r));
    S2 = group.mul(group.mul(group.exp(gG1, group.neg(alpha)), group.exp(v1G1, r)), group.exp(gG1, z1));
    S3 = group.exp(gbG2, group.neg(z1));
    S4 = group.mul(group.exp(v2G1, r), group.exp(gG1, z2));
    S5 = group.exp(gbG2, group.neg(z2));
    S6 = group.exp(gbG1, r2);
    S7 = group.exp(gG2, r1);
    SK = group.exp(group.mul(group.mul(group.exp(uG1, M), group.exp(wG1, tagk)), hG1), r1);
    sig.insert(0, S1);
    sig.insert(1, S2);
    sig.insert(2, S3);
    sig.insert(3, S4);
    sig.insert(4, S5);
    sig.insert(5, S6);
    sig.insert(6, S7);
    sig.insert(7, SK);
    sig.insert(8, tagk);
    return;
}

bool Dse09sig::verify(CharmList & vpk, string & m, CharmList & sig)
{
    GT A;
    G2 gG2;
    G1 ga1;
    G1 ga2;
    G1 gbG1;
    G2 gba1;
    G2 gba2;
    G1 hG1;
    G2 tau1G2;
    G1 tau1b;
    G2 tau2G2;
    G1 tau2b;
    G1 wG1;
    G2 S1;
    G1 S2;
    G2 S3;
    G1 S4;
    G2 S5;
    G1 S6;
    G2 S7;
    G1 SK;
    ZR tagk;
    ZR s1;
    ZR s2;
    ZR t;
    ZR tagc;
    ZR s;
    ZR M;
    ZR theta;
    
    A = vpk[0].getGT();
    gG2 = vpk[1].getG2();
    ga1 = vpk[2].getG1();
    ga2 = vpk[3].getG1();
    gbG1 = vpk[4].getG1();
    gba1 = vpk[5].getG2();
    gba2 = vpk[6].getG2();
    hG1 = vpk[7].getG1();
    tau1G2 = vpk[8].getG2();
    tau1b = vpk[9].getG1();
    tau2G2 = vpk[10].getG2();
    tau2b = vpk[11].getG1();
    wG1 = vpk[12].getG1();
    
    S1 = sig[0].getG2();
    S2 = sig[1].getG1();
    S3 = sig[2].getG2();
    S4 = sig[3].getG1();
    S5 = sig[4].getG2();
    S6 = sig[5].getG1();
    S7 = sig[6].getG2();
    SK = sig[7].getG1();
    tagk = sig[8].getZR();
    s1 = group.random(ZR_t);
    s2 = group.random(ZR_t);
    t = group.random(ZR_t);
    tagc = group.random(ZR_t);
    s = group.add(s1, s2);
    M = group.hashListToZR(m);
    theta = group.div(1, group.sub(tagc, tagk));
    if ( ( (group.mul(group.pair(group.exp(gbG1, s), S1), group.mul(group.pair(S2, group.exp(gba1, s1)), group.mul(group.pair(group.exp(ga1, s1), S3), group.mul(group.pair(S4, group.exp(gba2, s2)), group.pair(group.exp(ga2, s2), S5)))))) == (group.mul(group.pair(S6, group.mul(group.exp(tau1G2, s1), group.exp(tau2G2, s2))), group.mul(group.pair(group.mul(group.exp(tau1b, s1), group.mul(group.exp(tau2b, s2), group.mul(group.exp(wG1, -t), group.exp(hG1, t)))), S7), group.mul(group.exp(group.pair(SK, group.exp(gG2, -t)), theta), group.exp(A, s2))))) ) )
    {
        return true;
    }
    else
    {
        return false;
    }
}
