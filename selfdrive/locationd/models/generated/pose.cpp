#include "pose.h"

namespace {
#define DIM 18
#define EDIM 18
#define MEDIM 18
typedef void (*Hfun)(double *, double *, double *);
const static double MAHA_THRESH_4 = 7.814727903251177;
const static double MAHA_THRESH_10 = 7.814727903251177;
const static double MAHA_THRESH_13 = 7.814727903251177;
const static double MAHA_THRESH_14 = 7.814727903251177;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_812796242528121648) {
   out_812796242528121648[0] = delta_x[0] + nom_x[0];
   out_812796242528121648[1] = delta_x[1] + nom_x[1];
   out_812796242528121648[2] = delta_x[2] + nom_x[2];
   out_812796242528121648[3] = delta_x[3] + nom_x[3];
   out_812796242528121648[4] = delta_x[4] + nom_x[4];
   out_812796242528121648[5] = delta_x[5] + nom_x[5];
   out_812796242528121648[6] = delta_x[6] + nom_x[6];
   out_812796242528121648[7] = delta_x[7] + nom_x[7];
   out_812796242528121648[8] = delta_x[8] + nom_x[8];
   out_812796242528121648[9] = delta_x[9] + nom_x[9];
   out_812796242528121648[10] = delta_x[10] + nom_x[10];
   out_812796242528121648[11] = delta_x[11] + nom_x[11];
   out_812796242528121648[12] = delta_x[12] + nom_x[12];
   out_812796242528121648[13] = delta_x[13] + nom_x[13];
   out_812796242528121648[14] = delta_x[14] + nom_x[14];
   out_812796242528121648[15] = delta_x[15] + nom_x[15];
   out_812796242528121648[16] = delta_x[16] + nom_x[16];
   out_812796242528121648[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2630998712382937796) {
   out_2630998712382937796[0] = -nom_x[0] + true_x[0];
   out_2630998712382937796[1] = -nom_x[1] + true_x[1];
   out_2630998712382937796[2] = -nom_x[2] + true_x[2];
   out_2630998712382937796[3] = -nom_x[3] + true_x[3];
   out_2630998712382937796[4] = -nom_x[4] + true_x[4];
   out_2630998712382937796[5] = -nom_x[5] + true_x[5];
   out_2630998712382937796[6] = -nom_x[6] + true_x[6];
   out_2630998712382937796[7] = -nom_x[7] + true_x[7];
   out_2630998712382937796[8] = -nom_x[8] + true_x[8];
   out_2630998712382937796[9] = -nom_x[9] + true_x[9];
   out_2630998712382937796[10] = -nom_x[10] + true_x[10];
   out_2630998712382937796[11] = -nom_x[11] + true_x[11];
   out_2630998712382937796[12] = -nom_x[12] + true_x[12];
   out_2630998712382937796[13] = -nom_x[13] + true_x[13];
   out_2630998712382937796[14] = -nom_x[14] + true_x[14];
   out_2630998712382937796[15] = -nom_x[15] + true_x[15];
   out_2630998712382937796[16] = -nom_x[16] + true_x[16];
   out_2630998712382937796[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_8952125250503643232) {
   out_8952125250503643232[0] = 1.0;
   out_8952125250503643232[1] = 0.0;
   out_8952125250503643232[2] = 0.0;
   out_8952125250503643232[3] = 0.0;
   out_8952125250503643232[4] = 0.0;
   out_8952125250503643232[5] = 0.0;
   out_8952125250503643232[6] = 0.0;
   out_8952125250503643232[7] = 0.0;
   out_8952125250503643232[8] = 0.0;
   out_8952125250503643232[9] = 0.0;
   out_8952125250503643232[10] = 0.0;
   out_8952125250503643232[11] = 0.0;
   out_8952125250503643232[12] = 0.0;
   out_8952125250503643232[13] = 0.0;
   out_8952125250503643232[14] = 0.0;
   out_8952125250503643232[15] = 0.0;
   out_8952125250503643232[16] = 0.0;
   out_8952125250503643232[17] = 0.0;
   out_8952125250503643232[18] = 0.0;
   out_8952125250503643232[19] = 1.0;
   out_8952125250503643232[20] = 0.0;
   out_8952125250503643232[21] = 0.0;
   out_8952125250503643232[22] = 0.0;
   out_8952125250503643232[23] = 0.0;
   out_8952125250503643232[24] = 0.0;
   out_8952125250503643232[25] = 0.0;
   out_8952125250503643232[26] = 0.0;
   out_8952125250503643232[27] = 0.0;
   out_8952125250503643232[28] = 0.0;
   out_8952125250503643232[29] = 0.0;
   out_8952125250503643232[30] = 0.0;
   out_8952125250503643232[31] = 0.0;
   out_8952125250503643232[32] = 0.0;
   out_8952125250503643232[33] = 0.0;
   out_8952125250503643232[34] = 0.0;
   out_8952125250503643232[35] = 0.0;
   out_8952125250503643232[36] = 0.0;
   out_8952125250503643232[37] = 0.0;
   out_8952125250503643232[38] = 1.0;
   out_8952125250503643232[39] = 0.0;
   out_8952125250503643232[40] = 0.0;
   out_8952125250503643232[41] = 0.0;
   out_8952125250503643232[42] = 0.0;
   out_8952125250503643232[43] = 0.0;
   out_8952125250503643232[44] = 0.0;
   out_8952125250503643232[45] = 0.0;
   out_8952125250503643232[46] = 0.0;
   out_8952125250503643232[47] = 0.0;
   out_8952125250503643232[48] = 0.0;
   out_8952125250503643232[49] = 0.0;
   out_8952125250503643232[50] = 0.0;
   out_8952125250503643232[51] = 0.0;
   out_8952125250503643232[52] = 0.0;
   out_8952125250503643232[53] = 0.0;
   out_8952125250503643232[54] = 0.0;
   out_8952125250503643232[55] = 0.0;
   out_8952125250503643232[56] = 0.0;
   out_8952125250503643232[57] = 1.0;
   out_8952125250503643232[58] = 0.0;
   out_8952125250503643232[59] = 0.0;
   out_8952125250503643232[60] = 0.0;
   out_8952125250503643232[61] = 0.0;
   out_8952125250503643232[62] = 0.0;
   out_8952125250503643232[63] = 0.0;
   out_8952125250503643232[64] = 0.0;
   out_8952125250503643232[65] = 0.0;
   out_8952125250503643232[66] = 0.0;
   out_8952125250503643232[67] = 0.0;
   out_8952125250503643232[68] = 0.0;
   out_8952125250503643232[69] = 0.0;
   out_8952125250503643232[70] = 0.0;
   out_8952125250503643232[71] = 0.0;
   out_8952125250503643232[72] = 0.0;
   out_8952125250503643232[73] = 0.0;
   out_8952125250503643232[74] = 0.0;
   out_8952125250503643232[75] = 0.0;
   out_8952125250503643232[76] = 1.0;
   out_8952125250503643232[77] = 0.0;
   out_8952125250503643232[78] = 0.0;
   out_8952125250503643232[79] = 0.0;
   out_8952125250503643232[80] = 0.0;
   out_8952125250503643232[81] = 0.0;
   out_8952125250503643232[82] = 0.0;
   out_8952125250503643232[83] = 0.0;
   out_8952125250503643232[84] = 0.0;
   out_8952125250503643232[85] = 0.0;
   out_8952125250503643232[86] = 0.0;
   out_8952125250503643232[87] = 0.0;
   out_8952125250503643232[88] = 0.0;
   out_8952125250503643232[89] = 0.0;
   out_8952125250503643232[90] = 0.0;
   out_8952125250503643232[91] = 0.0;
   out_8952125250503643232[92] = 0.0;
   out_8952125250503643232[93] = 0.0;
   out_8952125250503643232[94] = 0.0;
   out_8952125250503643232[95] = 1.0;
   out_8952125250503643232[96] = 0.0;
   out_8952125250503643232[97] = 0.0;
   out_8952125250503643232[98] = 0.0;
   out_8952125250503643232[99] = 0.0;
   out_8952125250503643232[100] = 0.0;
   out_8952125250503643232[101] = 0.0;
   out_8952125250503643232[102] = 0.0;
   out_8952125250503643232[103] = 0.0;
   out_8952125250503643232[104] = 0.0;
   out_8952125250503643232[105] = 0.0;
   out_8952125250503643232[106] = 0.0;
   out_8952125250503643232[107] = 0.0;
   out_8952125250503643232[108] = 0.0;
   out_8952125250503643232[109] = 0.0;
   out_8952125250503643232[110] = 0.0;
   out_8952125250503643232[111] = 0.0;
   out_8952125250503643232[112] = 0.0;
   out_8952125250503643232[113] = 0.0;
   out_8952125250503643232[114] = 1.0;
   out_8952125250503643232[115] = 0.0;
   out_8952125250503643232[116] = 0.0;
   out_8952125250503643232[117] = 0.0;
   out_8952125250503643232[118] = 0.0;
   out_8952125250503643232[119] = 0.0;
   out_8952125250503643232[120] = 0.0;
   out_8952125250503643232[121] = 0.0;
   out_8952125250503643232[122] = 0.0;
   out_8952125250503643232[123] = 0.0;
   out_8952125250503643232[124] = 0.0;
   out_8952125250503643232[125] = 0.0;
   out_8952125250503643232[126] = 0.0;
   out_8952125250503643232[127] = 0.0;
   out_8952125250503643232[128] = 0.0;
   out_8952125250503643232[129] = 0.0;
   out_8952125250503643232[130] = 0.0;
   out_8952125250503643232[131] = 0.0;
   out_8952125250503643232[132] = 0.0;
   out_8952125250503643232[133] = 1.0;
   out_8952125250503643232[134] = 0.0;
   out_8952125250503643232[135] = 0.0;
   out_8952125250503643232[136] = 0.0;
   out_8952125250503643232[137] = 0.0;
   out_8952125250503643232[138] = 0.0;
   out_8952125250503643232[139] = 0.0;
   out_8952125250503643232[140] = 0.0;
   out_8952125250503643232[141] = 0.0;
   out_8952125250503643232[142] = 0.0;
   out_8952125250503643232[143] = 0.0;
   out_8952125250503643232[144] = 0.0;
   out_8952125250503643232[145] = 0.0;
   out_8952125250503643232[146] = 0.0;
   out_8952125250503643232[147] = 0.0;
   out_8952125250503643232[148] = 0.0;
   out_8952125250503643232[149] = 0.0;
   out_8952125250503643232[150] = 0.0;
   out_8952125250503643232[151] = 0.0;
   out_8952125250503643232[152] = 1.0;
   out_8952125250503643232[153] = 0.0;
   out_8952125250503643232[154] = 0.0;
   out_8952125250503643232[155] = 0.0;
   out_8952125250503643232[156] = 0.0;
   out_8952125250503643232[157] = 0.0;
   out_8952125250503643232[158] = 0.0;
   out_8952125250503643232[159] = 0.0;
   out_8952125250503643232[160] = 0.0;
   out_8952125250503643232[161] = 0.0;
   out_8952125250503643232[162] = 0.0;
   out_8952125250503643232[163] = 0.0;
   out_8952125250503643232[164] = 0.0;
   out_8952125250503643232[165] = 0.0;
   out_8952125250503643232[166] = 0.0;
   out_8952125250503643232[167] = 0.0;
   out_8952125250503643232[168] = 0.0;
   out_8952125250503643232[169] = 0.0;
   out_8952125250503643232[170] = 0.0;
   out_8952125250503643232[171] = 1.0;
   out_8952125250503643232[172] = 0.0;
   out_8952125250503643232[173] = 0.0;
   out_8952125250503643232[174] = 0.0;
   out_8952125250503643232[175] = 0.0;
   out_8952125250503643232[176] = 0.0;
   out_8952125250503643232[177] = 0.0;
   out_8952125250503643232[178] = 0.0;
   out_8952125250503643232[179] = 0.0;
   out_8952125250503643232[180] = 0.0;
   out_8952125250503643232[181] = 0.0;
   out_8952125250503643232[182] = 0.0;
   out_8952125250503643232[183] = 0.0;
   out_8952125250503643232[184] = 0.0;
   out_8952125250503643232[185] = 0.0;
   out_8952125250503643232[186] = 0.0;
   out_8952125250503643232[187] = 0.0;
   out_8952125250503643232[188] = 0.0;
   out_8952125250503643232[189] = 0.0;
   out_8952125250503643232[190] = 1.0;
   out_8952125250503643232[191] = 0.0;
   out_8952125250503643232[192] = 0.0;
   out_8952125250503643232[193] = 0.0;
   out_8952125250503643232[194] = 0.0;
   out_8952125250503643232[195] = 0.0;
   out_8952125250503643232[196] = 0.0;
   out_8952125250503643232[197] = 0.0;
   out_8952125250503643232[198] = 0.0;
   out_8952125250503643232[199] = 0.0;
   out_8952125250503643232[200] = 0.0;
   out_8952125250503643232[201] = 0.0;
   out_8952125250503643232[202] = 0.0;
   out_8952125250503643232[203] = 0.0;
   out_8952125250503643232[204] = 0.0;
   out_8952125250503643232[205] = 0.0;
   out_8952125250503643232[206] = 0.0;
   out_8952125250503643232[207] = 0.0;
   out_8952125250503643232[208] = 0.0;
   out_8952125250503643232[209] = 1.0;
   out_8952125250503643232[210] = 0.0;
   out_8952125250503643232[211] = 0.0;
   out_8952125250503643232[212] = 0.0;
   out_8952125250503643232[213] = 0.0;
   out_8952125250503643232[214] = 0.0;
   out_8952125250503643232[215] = 0.0;
   out_8952125250503643232[216] = 0.0;
   out_8952125250503643232[217] = 0.0;
   out_8952125250503643232[218] = 0.0;
   out_8952125250503643232[219] = 0.0;
   out_8952125250503643232[220] = 0.0;
   out_8952125250503643232[221] = 0.0;
   out_8952125250503643232[222] = 0.0;
   out_8952125250503643232[223] = 0.0;
   out_8952125250503643232[224] = 0.0;
   out_8952125250503643232[225] = 0.0;
   out_8952125250503643232[226] = 0.0;
   out_8952125250503643232[227] = 0.0;
   out_8952125250503643232[228] = 1.0;
   out_8952125250503643232[229] = 0.0;
   out_8952125250503643232[230] = 0.0;
   out_8952125250503643232[231] = 0.0;
   out_8952125250503643232[232] = 0.0;
   out_8952125250503643232[233] = 0.0;
   out_8952125250503643232[234] = 0.0;
   out_8952125250503643232[235] = 0.0;
   out_8952125250503643232[236] = 0.0;
   out_8952125250503643232[237] = 0.0;
   out_8952125250503643232[238] = 0.0;
   out_8952125250503643232[239] = 0.0;
   out_8952125250503643232[240] = 0.0;
   out_8952125250503643232[241] = 0.0;
   out_8952125250503643232[242] = 0.0;
   out_8952125250503643232[243] = 0.0;
   out_8952125250503643232[244] = 0.0;
   out_8952125250503643232[245] = 0.0;
   out_8952125250503643232[246] = 0.0;
   out_8952125250503643232[247] = 1.0;
   out_8952125250503643232[248] = 0.0;
   out_8952125250503643232[249] = 0.0;
   out_8952125250503643232[250] = 0.0;
   out_8952125250503643232[251] = 0.0;
   out_8952125250503643232[252] = 0.0;
   out_8952125250503643232[253] = 0.0;
   out_8952125250503643232[254] = 0.0;
   out_8952125250503643232[255] = 0.0;
   out_8952125250503643232[256] = 0.0;
   out_8952125250503643232[257] = 0.0;
   out_8952125250503643232[258] = 0.0;
   out_8952125250503643232[259] = 0.0;
   out_8952125250503643232[260] = 0.0;
   out_8952125250503643232[261] = 0.0;
   out_8952125250503643232[262] = 0.0;
   out_8952125250503643232[263] = 0.0;
   out_8952125250503643232[264] = 0.0;
   out_8952125250503643232[265] = 0.0;
   out_8952125250503643232[266] = 1.0;
   out_8952125250503643232[267] = 0.0;
   out_8952125250503643232[268] = 0.0;
   out_8952125250503643232[269] = 0.0;
   out_8952125250503643232[270] = 0.0;
   out_8952125250503643232[271] = 0.0;
   out_8952125250503643232[272] = 0.0;
   out_8952125250503643232[273] = 0.0;
   out_8952125250503643232[274] = 0.0;
   out_8952125250503643232[275] = 0.0;
   out_8952125250503643232[276] = 0.0;
   out_8952125250503643232[277] = 0.0;
   out_8952125250503643232[278] = 0.0;
   out_8952125250503643232[279] = 0.0;
   out_8952125250503643232[280] = 0.0;
   out_8952125250503643232[281] = 0.0;
   out_8952125250503643232[282] = 0.0;
   out_8952125250503643232[283] = 0.0;
   out_8952125250503643232[284] = 0.0;
   out_8952125250503643232[285] = 1.0;
   out_8952125250503643232[286] = 0.0;
   out_8952125250503643232[287] = 0.0;
   out_8952125250503643232[288] = 0.0;
   out_8952125250503643232[289] = 0.0;
   out_8952125250503643232[290] = 0.0;
   out_8952125250503643232[291] = 0.0;
   out_8952125250503643232[292] = 0.0;
   out_8952125250503643232[293] = 0.0;
   out_8952125250503643232[294] = 0.0;
   out_8952125250503643232[295] = 0.0;
   out_8952125250503643232[296] = 0.0;
   out_8952125250503643232[297] = 0.0;
   out_8952125250503643232[298] = 0.0;
   out_8952125250503643232[299] = 0.0;
   out_8952125250503643232[300] = 0.0;
   out_8952125250503643232[301] = 0.0;
   out_8952125250503643232[302] = 0.0;
   out_8952125250503643232[303] = 0.0;
   out_8952125250503643232[304] = 1.0;
   out_8952125250503643232[305] = 0.0;
   out_8952125250503643232[306] = 0.0;
   out_8952125250503643232[307] = 0.0;
   out_8952125250503643232[308] = 0.0;
   out_8952125250503643232[309] = 0.0;
   out_8952125250503643232[310] = 0.0;
   out_8952125250503643232[311] = 0.0;
   out_8952125250503643232[312] = 0.0;
   out_8952125250503643232[313] = 0.0;
   out_8952125250503643232[314] = 0.0;
   out_8952125250503643232[315] = 0.0;
   out_8952125250503643232[316] = 0.0;
   out_8952125250503643232[317] = 0.0;
   out_8952125250503643232[318] = 0.0;
   out_8952125250503643232[319] = 0.0;
   out_8952125250503643232[320] = 0.0;
   out_8952125250503643232[321] = 0.0;
   out_8952125250503643232[322] = 0.0;
   out_8952125250503643232[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_3519678704568830866) {
   out_3519678704568830866[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_3519678704568830866[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_3519678704568830866[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_3519678704568830866[3] = dt*state[12] + state[3];
   out_3519678704568830866[4] = dt*state[13] + state[4];
   out_3519678704568830866[5] = dt*state[14] + state[5];
   out_3519678704568830866[6] = state[6];
   out_3519678704568830866[7] = state[7];
   out_3519678704568830866[8] = state[8];
   out_3519678704568830866[9] = state[9];
   out_3519678704568830866[10] = state[10];
   out_3519678704568830866[11] = state[11];
   out_3519678704568830866[12] = state[12];
   out_3519678704568830866[13] = state[13];
   out_3519678704568830866[14] = state[14];
   out_3519678704568830866[15] = state[15];
   out_3519678704568830866[16] = state[16];
   out_3519678704568830866[17] = state[17];
}
void F_fun(double *state, double dt, double *out_6750093296288889328) {
   out_6750093296288889328[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6750093296288889328[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6750093296288889328[2] = 0;
   out_6750093296288889328[3] = 0;
   out_6750093296288889328[4] = 0;
   out_6750093296288889328[5] = 0;
   out_6750093296288889328[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6750093296288889328[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6750093296288889328[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6750093296288889328[9] = 0;
   out_6750093296288889328[10] = 0;
   out_6750093296288889328[11] = 0;
   out_6750093296288889328[12] = 0;
   out_6750093296288889328[13] = 0;
   out_6750093296288889328[14] = 0;
   out_6750093296288889328[15] = 0;
   out_6750093296288889328[16] = 0;
   out_6750093296288889328[17] = 0;
   out_6750093296288889328[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6750093296288889328[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6750093296288889328[20] = 0;
   out_6750093296288889328[21] = 0;
   out_6750093296288889328[22] = 0;
   out_6750093296288889328[23] = 0;
   out_6750093296288889328[24] = 0;
   out_6750093296288889328[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6750093296288889328[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6750093296288889328[27] = 0;
   out_6750093296288889328[28] = 0;
   out_6750093296288889328[29] = 0;
   out_6750093296288889328[30] = 0;
   out_6750093296288889328[31] = 0;
   out_6750093296288889328[32] = 0;
   out_6750093296288889328[33] = 0;
   out_6750093296288889328[34] = 0;
   out_6750093296288889328[35] = 0;
   out_6750093296288889328[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6750093296288889328[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6750093296288889328[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6750093296288889328[39] = 0;
   out_6750093296288889328[40] = 0;
   out_6750093296288889328[41] = 0;
   out_6750093296288889328[42] = 0;
   out_6750093296288889328[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6750093296288889328[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6750093296288889328[45] = 0;
   out_6750093296288889328[46] = 0;
   out_6750093296288889328[47] = 0;
   out_6750093296288889328[48] = 0;
   out_6750093296288889328[49] = 0;
   out_6750093296288889328[50] = 0;
   out_6750093296288889328[51] = 0;
   out_6750093296288889328[52] = 0;
   out_6750093296288889328[53] = 0;
   out_6750093296288889328[54] = 0;
   out_6750093296288889328[55] = 0;
   out_6750093296288889328[56] = 0;
   out_6750093296288889328[57] = 1;
   out_6750093296288889328[58] = 0;
   out_6750093296288889328[59] = 0;
   out_6750093296288889328[60] = 0;
   out_6750093296288889328[61] = 0;
   out_6750093296288889328[62] = 0;
   out_6750093296288889328[63] = 0;
   out_6750093296288889328[64] = 0;
   out_6750093296288889328[65] = 0;
   out_6750093296288889328[66] = dt;
   out_6750093296288889328[67] = 0;
   out_6750093296288889328[68] = 0;
   out_6750093296288889328[69] = 0;
   out_6750093296288889328[70] = 0;
   out_6750093296288889328[71] = 0;
   out_6750093296288889328[72] = 0;
   out_6750093296288889328[73] = 0;
   out_6750093296288889328[74] = 0;
   out_6750093296288889328[75] = 0;
   out_6750093296288889328[76] = 1;
   out_6750093296288889328[77] = 0;
   out_6750093296288889328[78] = 0;
   out_6750093296288889328[79] = 0;
   out_6750093296288889328[80] = 0;
   out_6750093296288889328[81] = 0;
   out_6750093296288889328[82] = 0;
   out_6750093296288889328[83] = 0;
   out_6750093296288889328[84] = 0;
   out_6750093296288889328[85] = dt;
   out_6750093296288889328[86] = 0;
   out_6750093296288889328[87] = 0;
   out_6750093296288889328[88] = 0;
   out_6750093296288889328[89] = 0;
   out_6750093296288889328[90] = 0;
   out_6750093296288889328[91] = 0;
   out_6750093296288889328[92] = 0;
   out_6750093296288889328[93] = 0;
   out_6750093296288889328[94] = 0;
   out_6750093296288889328[95] = 1;
   out_6750093296288889328[96] = 0;
   out_6750093296288889328[97] = 0;
   out_6750093296288889328[98] = 0;
   out_6750093296288889328[99] = 0;
   out_6750093296288889328[100] = 0;
   out_6750093296288889328[101] = 0;
   out_6750093296288889328[102] = 0;
   out_6750093296288889328[103] = 0;
   out_6750093296288889328[104] = dt;
   out_6750093296288889328[105] = 0;
   out_6750093296288889328[106] = 0;
   out_6750093296288889328[107] = 0;
   out_6750093296288889328[108] = 0;
   out_6750093296288889328[109] = 0;
   out_6750093296288889328[110] = 0;
   out_6750093296288889328[111] = 0;
   out_6750093296288889328[112] = 0;
   out_6750093296288889328[113] = 0;
   out_6750093296288889328[114] = 1;
   out_6750093296288889328[115] = 0;
   out_6750093296288889328[116] = 0;
   out_6750093296288889328[117] = 0;
   out_6750093296288889328[118] = 0;
   out_6750093296288889328[119] = 0;
   out_6750093296288889328[120] = 0;
   out_6750093296288889328[121] = 0;
   out_6750093296288889328[122] = 0;
   out_6750093296288889328[123] = 0;
   out_6750093296288889328[124] = 0;
   out_6750093296288889328[125] = 0;
   out_6750093296288889328[126] = 0;
   out_6750093296288889328[127] = 0;
   out_6750093296288889328[128] = 0;
   out_6750093296288889328[129] = 0;
   out_6750093296288889328[130] = 0;
   out_6750093296288889328[131] = 0;
   out_6750093296288889328[132] = 0;
   out_6750093296288889328[133] = 1;
   out_6750093296288889328[134] = 0;
   out_6750093296288889328[135] = 0;
   out_6750093296288889328[136] = 0;
   out_6750093296288889328[137] = 0;
   out_6750093296288889328[138] = 0;
   out_6750093296288889328[139] = 0;
   out_6750093296288889328[140] = 0;
   out_6750093296288889328[141] = 0;
   out_6750093296288889328[142] = 0;
   out_6750093296288889328[143] = 0;
   out_6750093296288889328[144] = 0;
   out_6750093296288889328[145] = 0;
   out_6750093296288889328[146] = 0;
   out_6750093296288889328[147] = 0;
   out_6750093296288889328[148] = 0;
   out_6750093296288889328[149] = 0;
   out_6750093296288889328[150] = 0;
   out_6750093296288889328[151] = 0;
   out_6750093296288889328[152] = 1;
   out_6750093296288889328[153] = 0;
   out_6750093296288889328[154] = 0;
   out_6750093296288889328[155] = 0;
   out_6750093296288889328[156] = 0;
   out_6750093296288889328[157] = 0;
   out_6750093296288889328[158] = 0;
   out_6750093296288889328[159] = 0;
   out_6750093296288889328[160] = 0;
   out_6750093296288889328[161] = 0;
   out_6750093296288889328[162] = 0;
   out_6750093296288889328[163] = 0;
   out_6750093296288889328[164] = 0;
   out_6750093296288889328[165] = 0;
   out_6750093296288889328[166] = 0;
   out_6750093296288889328[167] = 0;
   out_6750093296288889328[168] = 0;
   out_6750093296288889328[169] = 0;
   out_6750093296288889328[170] = 0;
   out_6750093296288889328[171] = 1;
   out_6750093296288889328[172] = 0;
   out_6750093296288889328[173] = 0;
   out_6750093296288889328[174] = 0;
   out_6750093296288889328[175] = 0;
   out_6750093296288889328[176] = 0;
   out_6750093296288889328[177] = 0;
   out_6750093296288889328[178] = 0;
   out_6750093296288889328[179] = 0;
   out_6750093296288889328[180] = 0;
   out_6750093296288889328[181] = 0;
   out_6750093296288889328[182] = 0;
   out_6750093296288889328[183] = 0;
   out_6750093296288889328[184] = 0;
   out_6750093296288889328[185] = 0;
   out_6750093296288889328[186] = 0;
   out_6750093296288889328[187] = 0;
   out_6750093296288889328[188] = 0;
   out_6750093296288889328[189] = 0;
   out_6750093296288889328[190] = 1;
   out_6750093296288889328[191] = 0;
   out_6750093296288889328[192] = 0;
   out_6750093296288889328[193] = 0;
   out_6750093296288889328[194] = 0;
   out_6750093296288889328[195] = 0;
   out_6750093296288889328[196] = 0;
   out_6750093296288889328[197] = 0;
   out_6750093296288889328[198] = 0;
   out_6750093296288889328[199] = 0;
   out_6750093296288889328[200] = 0;
   out_6750093296288889328[201] = 0;
   out_6750093296288889328[202] = 0;
   out_6750093296288889328[203] = 0;
   out_6750093296288889328[204] = 0;
   out_6750093296288889328[205] = 0;
   out_6750093296288889328[206] = 0;
   out_6750093296288889328[207] = 0;
   out_6750093296288889328[208] = 0;
   out_6750093296288889328[209] = 1;
   out_6750093296288889328[210] = 0;
   out_6750093296288889328[211] = 0;
   out_6750093296288889328[212] = 0;
   out_6750093296288889328[213] = 0;
   out_6750093296288889328[214] = 0;
   out_6750093296288889328[215] = 0;
   out_6750093296288889328[216] = 0;
   out_6750093296288889328[217] = 0;
   out_6750093296288889328[218] = 0;
   out_6750093296288889328[219] = 0;
   out_6750093296288889328[220] = 0;
   out_6750093296288889328[221] = 0;
   out_6750093296288889328[222] = 0;
   out_6750093296288889328[223] = 0;
   out_6750093296288889328[224] = 0;
   out_6750093296288889328[225] = 0;
   out_6750093296288889328[226] = 0;
   out_6750093296288889328[227] = 0;
   out_6750093296288889328[228] = 1;
   out_6750093296288889328[229] = 0;
   out_6750093296288889328[230] = 0;
   out_6750093296288889328[231] = 0;
   out_6750093296288889328[232] = 0;
   out_6750093296288889328[233] = 0;
   out_6750093296288889328[234] = 0;
   out_6750093296288889328[235] = 0;
   out_6750093296288889328[236] = 0;
   out_6750093296288889328[237] = 0;
   out_6750093296288889328[238] = 0;
   out_6750093296288889328[239] = 0;
   out_6750093296288889328[240] = 0;
   out_6750093296288889328[241] = 0;
   out_6750093296288889328[242] = 0;
   out_6750093296288889328[243] = 0;
   out_6750093296288889328[244] = 0;
   out_6750093296288889328[245] = 0;
   out_6750093296288889328[246] = 0;
   out_6750093296288889328[247] = 1;
   out_6750093296288889328[248] = 0;
   out_6750093296288889328[249] = 0;
   out_6750093296288889328[250] = 0;
   out_6750093296288889328[251] = 0;
   out_6750093296288889328[252] = 0;
   out_6750093296288889328[253] = 0;
   out_6750093296288889328[254] = 0;
   out_6750093296288889328[255] = 0;
   out_6750093296288889328[256] = 0;
   out_6750093296288889328[257] = 0;
   out_6750093296288889328[258] = 0;
   out_6750093296288889328[259] = 0;
   out_6750093296288889328[260] = 0;
   out_6750093296288889328[261] = 0;
   out_6750093296288889328[262] = 0;
   out_6750093296288889328[263] = 0;
   out_6750093296288889328[264] = 0;
   out_6750093296288889328[265] = 0;
   out_6750093296288889328[266] = 1;
   out_6750093296288889328[267] = 0;
   out_6750093296288889328[268] = 0;
   out_6750093296288889328[269] = 0;
   out_6750093296288889328[270] = 0;
   out_6750093296288889328[271] = 0;
   out_6750093296288889328[272] = 0;
   out_6750093296288889328[273] = 0;
   out_6750093296288889328[274] = 0;
   out_6750093296288889328[275] = 0;
   out_6750093296288889328[276] = 0;
   out_6750093296288889328[277] = 0;
   out_6750093296288889328[278] = 0;
   out_6750093296288889328[279] = 0;
   out_6750093296288889328[280] = 0;
   out_6750093296288889328[281] = 0;
   out_6750093296288889328[282] = 0;
   out_6750093296288889328[283] = 0;
   out_6750093296288889328[284] = 0;
   out_6750093296288889328[285] = 1;
   out_6750093296288889328[286] = 0;
   out_6750093296288889328[287] = 0;
   out_6750093296288889328[288] = 0;
   out_6750093296288889328[289] = 0;
   out_6750093296288889328[290] = 0;
   out_6750093296288889328[291] = 0;
   out_6750093296288889328[292] = 0;
   out_6750093296288889328[293] = 0;
   out_6750093296288889328[294] = 0;
   out_6750093296288889328[295] = 0;
   out_6750093296288889328[296] = 0;
   out_6750093296288889328[297] = 0;
   out_6750093296288889328[298] = 0;
   out_6750093296288889328[299] = 0;
   out_6750093296288889328[300] = 0;
   out_6750093296288889328[301] = 0;
   out_6750093296288889328[302] = 0;
   out_6750093296288889328[303] = 0;
   out_6750093296288889328[304] = 1;
   out_6750093296288889328[305] = 0;
   out_6750093296288889328[306] = 0;
   out_6750093296288889328[307] = 0;
   out_6750093296288889328[308] = 0;
   out_6750093296288889328[309] = 0;
   out_6750093296288889328[310] = 0;
   out_6750093296288889328[311] = 0;
   out_6750093296288889328[312] = 0;
   out_6750093296288889328[313] = 0;
   out_6750093296288889328[314] = 0;
   out_6750093296288889328[315] = 0;
   out_6750093296288889328[316] = 0;
   out_6750093296288889328[317] = 0;
   out_6750093296288889328[318] = 0;
   out_6750093296288889328[319] = 0;
   out_6750093296288889328[320] = 0;
   out_6750093296288889328[321] = 0;
   out_6750093296288889328[322] = 0;
   out_6750093296288889328[323] = 1;
}
void h_4(double *state, double *unused, double *out_1078897140345555822) {
   out_1078897140345555822[0] = state[6] + state[9];
   out_1078897140345555822[1] = state[7] + state[10];
   out_1078897140345555822[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_850583411531230682) {
   out_850583411531230682[0] = 0;
   out_850583411531230682[1] = 0;
   out_850583411531230682[2] = 0;
   out_850583411531230682[3] = 0;
   out_850583411531230682[4] = 0;
   out_850583411531230682[5] = 0;
   out_850583411531230682[6] = 1;
   out_850583411531230682[7] = 0;
   out_850583411531230682[8] = 0;
   out_850583411531230682[9] = 1;
   out_850583411531230682[10] = 0;
   out_850583411531230682[11] = 0;
   out_850583411531230682[12] = 0;
   out_850583411531230682[13] = 0;
   out_850583411531230682[14] = 0;
   out_850583411531230682[15] = 0;
   out_850583411531230682[16] = 0;
   out_850583411531230682[17] = 0;
   out_850583411531230682[18] = 0;
   out_850583411531230682[19] = 0;
   out_850583411531230682[20] = 0;
   out_850583411531230682[21] = 0;
   out_850583411531230682[22] = 0;
   out_850583411531230682[23] = 0;
   out_850583411531230682[24] = 0;
   out_850583411531230682[25] = 1;
   out_850583411531230682[26] = 0;
   out_850583411531230682[27] = 0;
   out_850583411531230682[28] = 1;
   out_850583411531230682[29] = 0;
   out_850583411531230682[30] = 0;
   out_850583411531230682[31] = 0;
   out_850583411531230682[32] = 0;
   out_850583411531230682[33] = 0;
   out_850583411531230682[34] = 0;
   out_850583411531230682[35] = 0;
   out_850583411531230682[36] = 0;
   out_850583411531230682[37] = 0;
   out_850583411531230682[38] = 0;
   out_850583411531230682[39] = 0;
   out_850583411531230682[40] = 0;
   out_850583411531230682[41] = 0;
   out_850583411531230682[42] = 0;
   out_850583411531230682[43] = 0;
   out_850583411531230682[44] = 1;
   out_850583411531230682[45] = 0;
   out_850583411531230682[46] = 0;
   out_850583411531230682[47] = 1;
   out_850583411531230682[48] = 0;
   out_850583411531230682[49] = 0;
   out_850583411531230682[50] = 0;
   out_850583411531230682[51] = 0;
   out_850583411531230682[52] = 0;
   out_850583411531230682[53] = 0;
}
void h_10(double *state, double *unused, double *out_3641708848879017741) {
   out_3641708848879017741[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_3641708848879017741[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_3641708848879017741[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_7494820718027871329) {
   out_7494820718027871329[0] = 0;
   out_7494820718027871329[1] = 9.8100000000000005*cos(state[1]);
   out_7494820718027871329[2] = 0;
   out_7494820718027871329[3] = 0;
   out_7494820718027871329[4] = -state[8];
   out_7494820718027871329[5] = state[7];
   out_7494820718027871329[6] = 0;
   out_7494820718027871329[7] = state[5];
   out_7494820718027871329[8] = -state[4];
   out_7494820718027871329[9] = 0;
   out_7494820718027871329[10] = 0;
   out_7494820718027871329[11] = 0;
   out_7494820718027871329[12] = 1;
   out_7494820718027871329[13] = 0;
   out_7494820718027871329[14] = 0;
   out_7494820718027871329[15] = 1;
   out_7494820718027871329[16] = 0;
   out_7494820718027871329[17] = 0;
   out_7494820718027871329[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_7494820718027871329[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_7494820718027871329[20] = 0;
   out_7494820718027871329[21] = state[8];
   out_7494820718027871329[22] = 0;
   out_7494820718027871329[23] = -state[6];
   out_7494820718027871329[24] = -state[5];
   out_7494820718027871329[25] = 0;
   out_7494820718027871329[26] = state[3];
   out_7494820718027871329[27] = 0;
   out_7494820718027871329[28] = 0;
   out_7494820718027871329[29] = 0;
   out_7494820718027871329[30] = 0;
   out_7494820718027871329[31] = 1;
   out_7494820718027871329[32] = 0;
   out_7494820718027871329[33] = 0;
   out_7494820718027871329[34] = 1;
   out_7494820718027871329[35] = 0;
   out_7494820718027871329[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_7494820718027871329[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_7494820718027871329[38] = 0;
   out_7494820718027871329[39] = -state[7];
   out_7494820718027871329[40] = state[6];
   out_7494820718027871329[41] = 0;
   out_7494820718027871329[42] = state[4];
   out_7494820718027871329[43] = -state[3];
   out_7494820718027871329[44] = 0;
   out_7494820718027871329[45] = 0;
   out_7494820718027871329[46] = 0;
   out_7494820718027871329[47] = 0;
   out_7494820718027871329[48] = 0;
   out_7494820718027871329[49] = 0;
   out_7494820718027871329[50] = 1;
   out_7494820718027871329[51] = 0;
   out_7494820718027871329[52] = 0;
   out_7494820718027871329[53] = 1;
}
void h_13(double *state, double *unused, double *out_515642654693887905) {
   out_515642654693887905[0] = state[3];
   out_515642654693887905[1] = state[4];
   out_515642654693887905[2] = state[5];
}
void H_13(double *state, double *unused, double *out_4062857236863563483) {
   out_4062857236863563483[0] = 0;
   out_4062857236863563483[1] = 0;
   out_4062857236863563483[2] = 0;
   out_4062857236863563483[3] = 1;
   out_4062857236863563483[4] = 0;
   out_4062857236863563483[5] = 0;
   out_4062857236863563483[6] = 0;
   out_4062857236863563483[7] = 0;
   out_4062857236863563483[8] = 0;
   out_4062857236863563483[9] = 0;
   out_4062857236863563483[10] = 0;
   out_4062857236863563483[11] = 0;
   out_4062857236863563483[12] = 0;
   out_4062857236863563483[13] = 0;
   out_4062857236863563483[14] = 0;
   out_4062857236863563483[15] = 0;
   out_4062857236863563483[16] = 0;
   out_4062857236863563483[17] = 0;
   out_4062857236863563483[18] = 0;
   out_4062857236863563483[19] = 0;
   out_4062857236863563483[20] = 0;
   out_4062857236863563483[21] = 0;
   out_4062857236863563483[22] = 1;
   out_4062857236863563483[23] = 0;
   out_4062857236863563483[24] = 0;
   out_4062857236863563483[25] = 0;
   out_4062857236863563483[26] = 0;
   out_4062857236863563483[27] = 0;
   out_4062857236863563483[28] = 0;
   out_4062857236863563483[29] = 0;
   out_4062857236863563483[30] = 0;
   out_4062857236863563483[31] = 0;
   out_4062857236863563483[32] = 0;
   out_4062857236863563483[33] = 0;
   out_4062857236863563483[34] = 0;
   out_4062857236863563483[35] = 0;
   out_4062857236863563483[36] = 0;
   out_4062857236863563483[37] = 0;
   out_4062857236863563483[38] = 0;
   out_4062857236863563483[39] = 0;
   out_4062857236863563483[40] = 0;
   out_4062857236863563483[41] = 1;
   out_4062857236863563483[42] = 0;
   out_4062857236863563483[43] = 0;
   out_4062857236863563483[44] = 0;
   out_4062857236863563483[45] = 0;
   out_4062857236863563483[46] = 0;
   out_4062857236863563483[47] = 0;
   out_4062857236863563483[48] = 0;
   out_4062857236863563483[49] = 0;
   out_4062857236863563483[50] = 0;
   out_4062857236863563483[51] = 0;
   out_4062857236863563483[52] = 0;
   out_4062857236863563483[53] = 0;
}
void h_14(double *state, double *unused, double *out_1617663395634793849) {
   out_1617663395634793849[0] = state[6];
   out_1617663395634793849[1] = state[7];
   out_1617663395634793849[2] = state[8];
}
void H_14(double *state, double *unused, double *out_4813824267870715211) {
   out_4813824267870715211[0] = 0;
   out_4813824267870715211[1] = 0;
   out_4813824267870715211[2] = 0;
   out_4813824267870715211[3] = 0;
   out_4813824267870715211[4] = 0;
   out_4813824267870715211[5] = 0;
   out_4813824267870715211[6] = 1;
   out_4813824267870715211[7] = 0;
   out_4813824267870715211[8] = 0;
   out_4813824267870715211[9] = 0;
   out_4813824267870715211[10] = 0;
   out_4813824267870715211[11] = 0;
   out_4813824267870715211[12] = 0;
   out_4813824267870715211[13] = 0;
   out_4813824267870715211[14] = 0;
   out_4813824267870715211[15] = 0;
   out_4813824267870715211[16] = 0;
   out_4813824267870715211[17] = 0;
   out_4813824267870715211[18] = 0;
   out_4813824267870715211[19] = 0;
   out_4813824267870715211[20] = 0;
   out_4813824267870715211[21] = 0;
   out_4813824267870715211[22] = 0;
   out_4813824267870715211[23] = 0;
   out_4813824267870715211[24] = 0;
   out_4813824267870715211[25] = 1;
   out_4813824267870715211[26] = 0;
   out_4813824267870715211[27] = 0;
   out_4813824267870715211[28] = 0;
   out_4813824267870715211[29] = 0;
   out_4813824267870715211[30] = 0;
   out_4813824267870715211[31] = 0;
   out_4813824267870715211[32] = 0;
   out_4813824267870715211[33] = 0;
   out_4813824267870715211[34] = 0;
   out_4813824267870715211[35] = 0;
   out_4813824267870715211[36] = 0;
   out_4813824267870715211[37] = 0;
   out_4813824267870715211[38] = 0;
   out_4813824267870715211[39] = 0;
   out_4813824267870715211[40] = 0;
   out_4813824267870715211[41] = 0;
   out_4813824267870715211[42] = 0;
   out_4813824267870715211[43] = 0;
   out_4813824267870715211[44] = 1;
   out_4813824267870715211[45] = 0;
   out_4813824267870715211[46] = 0;
   out_4813824267870715211[47] = 0;
   out_4813824267870715211[48] = 0;
   out_4813824267870715211[49] = 0;
   out_4813824267870715211[50] = 0;
   out_4813824267870715211[51] = 0;
   out_4813824267870715211[52] = 0;
   out_4813824267870715211[53] = 0;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_4, H_4, NULL, in_z, in_R, in_ea, MAHA_THRESH_4);
}
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_10, H_10, NULL, in_z, in_R, in_ea, MAHA_THRESH_10);
}
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_13, H_13, NULL, in_z, in_R, in_ea, MAHA_THRESH_13);
}
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_14, H_14, NULL, in_z, in_R, in_ea, MAHA_THRESH_14);
}
void pose_err_fun(double *nom_x, double *delta_x, double *out_812796242528121648) {
  err_fun(nom_x, delta_x, out_812796242528121648);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2630998712382937796) {
  inv_err_fun(nom_x, true_x, out_2630998712382937796);
}
void pose_H_mod_fun(double *state, double *out_8952125250503643232) {
  H_mod_fun(state, out_8952125250503643232);
}
void pose_f_fun(double *state, double dt, double *out_3519678704568830866) {
  f_fun(state,  dt, out_3519678704568830866);
}
void pose_F_fun(double *state, double dt, double *out_6750093296288889328) {
  F_fun(state,  dt, out_6750093296288889328);
}
void pose_h_4(double *state, double *unused, double *out_1078897140345555822) {
  h_4(state, unused, out_1078897140345555822);
}
void pose_H_4(double *state, double *unused, double *out_850583411531230682) {
  H_4(state, unused, out_850583411531230682);
}
void pose_h_10(double *state, double *unused, double *out_3641708848879017741) {
  h_10(state, unused, out_3641708848879017741);
}
void pose_H_10(double *state, double *unused, double *out_7494820718027871329) {
  H_10(state, unused, out_7494820718027871329);
}
void pose_h_13(double *state, double *unused, double *out_515642654693887905) {
  h_13(state, unused, out_515642654693887905);
}
void pose_H_13(double *state, double *unused, double *out_4062857236863563483) {
  H_13(state, unused, out_4062857236863563483);
}
void pose_h_14(double *state, double *unused, double *out_1617663395634793849) {
  h_14(state, unused, out_1617663395634793849);
}
void pose_H_14(double *state, double *unused, double *out_4813824267870715211) {
  H_14(state, unused, out_4813824267870715211);
}
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
}

const EKF pose = {
  .name = "pose",
  .kinds = { 4, 10, 13, 14 },
  .feature_kinds = {  },
  .f_fun = pose_f_fun,
  .F_fun = pose_F_fun,
  .err_fun = pose_err_fun,
  .inv_err_fun = pose_inv_err_fun,
  .H_mod_fun = pose_H_mod_fun,
  .predict = pose_predict,
  .hs = {
    { 4, pose_h_4 },
    { 10, pose_h_10 },
    { 13, pose_h_13 },
    { 14, pose_h_14 },
  },
  .Hs = {
    { 4, pose_H_4 },
    { 10, pose_H_10 },
    { 13, pose_H_13 },
    { 14, pose_H_14 },
  },
  .updates = {
    { 4, pose_update_4 },
    { 10, pose_update_10 },
    { 13, pose_update_13 },
    { 14, pose_update_14 },
  },
  .Hes = {
  },
  .sets = {
  },
  .extra_routines = {
  },
};

ekf_lib_init(pose)
