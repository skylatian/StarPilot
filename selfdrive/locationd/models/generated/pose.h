#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_812796242528121648);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2630998712382937796);
void pose_H_mod_fun(double *state, double *out_8952125250503643232);
void pose_f_fun(double *state, double dt, double *out_3519678704568830866);
void pose_F_fun(double *state, double dt, double *out_6750093296288889328);
void pose_h_4(double *state, double *unused, double *out_1078897140345555822);
void pose_H_4(double *state, double *unused, double *out_850583411531230682);
void pose_h_10(double *state, double *unused, double *out_3641708848879017741);
void pose_H_10(double *state, double *unused, double *out_7494820718027871329);
void pose_h_13(double *state, double *unused, double *out_515642654693887905);
void pose_H_13(double *state, double *unused, double *out_4062857236863563483);
void pose_h_14(double *state, double *unused, double *out_1617663395634793849);
void pose_H_14(double *state, double *unused, double *out_4813824267870715211);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}