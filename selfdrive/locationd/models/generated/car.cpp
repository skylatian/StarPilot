#include "car.h"

namespace {
#define DIM 9
#define EDIM 9
#define MEDIM 9
typedef void (*Hfun)(double *, double *, double *);

double mass;

void set_mass(double x){ mass = x;}

double rotational_inertia;

void set_rotational_inertia(double x){ rotational_inertia = x;}

double center_to_front;

void set_center_to_front(double x){ center_to_front = x;}

double center_to_rear;

void set_center_to_rear(double x){ center_to_rear = x;}

double stiffness_front;

void set_stiffness_front(double x){ stiffness_front = x;}

double stiffness_rear;

void set_stiffness_rear(double x){ stiffness_rear = x;}
const static double MAHA_THRESH_25 = 3.8414588206941227;
const static double MAHA_THRESH_24 = 5.991464547107981;
const static double MAHA_THRESH_30 = 3.8414588206941227;
const static double MAHA_THRESH_26 = 3.8414588206941227;
const static double MAHA_THRESH_27 = 3.8414588206941227;
const static double MAHA_THRESH_29 = 3.8414588206941227;
const static double MAHA_THRESH_28 = 3.8414588206941227;
const static double MAHA_THRESH_31 = 3.8414588206941227;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_1976458697034392713) {
   out_1976458697034392713[0] = delta_x[0] + nom_x[0];
   out_1976458697034392713[1] = delta_x[1] + nom_x[1];
   out_1976458697034392713[2] = delta_x[2] + nom_x[2];
   out_1976458697034392713[3] = delta_x[3] + nom_x[3];
   out_1976458697034392713[4] = delta_x[4] + nom_x[4];
   out_1976458697034392713[5] = delta_x[5] + nom_x[5];
   out_1976458697034392713[6] = delta_x[6] + nom_x[6];
   out_1976458697034392713[7] = delta_x[7] + nom_x[7];
   out_1976458697034392713[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_8774680380747325588) {
   out_8774680380747325588[0] = -nom_x[0] + true_x[0];
   out_8774680380747325588[1] = -nom_x[1] + true_x[1];
   out_8774680380747325588[2] = -nom_x[2] + true_x[2];
   out_8774680380747325588[3] = -nom_x[3] + true_x[3];
   out_8774680380747325588[4] = -nom_x[4] + true_x[4];
   out_8774680380747325588[5] = -nom_x[5] + true_x[5];
   out_8774680380747325588[6] = -nom_x[6] + true_x[6];
   out_8774680380747325588[7] = -nom_x[7] + true_x[7];
   out_8774680380747325588[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_1571472922248018296) {
   out_1571472922248018296[0] = 1.0;
   out_1571472922248018296[1] = 0.0;
   out_1571472922248018296[2] = 0.0;
   out_1571472922248018296[3] = 0.0;
   out_1571472922248018296[4] = 0.0;
   out_1571472922248018296[5] = 0.0;
   out_1571472922248018296[6] = 0.0;
   out_1571472922248018296[7] = 0.0;
   out_1571472922248018296[8] = 0.0;
   out_1571472922248018296[9] = 0.0;
   out_1571472922248018296[10] = 1.0;
   out_1571472922248018296[11] = 0.0;
   out_1571472922248018296[12] = 0.0;
   out_1571472922248018296[13] = 0.0;
   out_1571472922248018296[14] = 0.0;
   out_1571472922248018296[15] = 0.0;
   out_1571472922248018296[16] = 0.0;
   out_1571472922248018296[17] = 0.0;
   out_1571472922248018296[18] = 0.0;
   out_1571472922248018296[19] = 0.0;
   out_1571472922248018296[20] = 1.0;
   out_1571472922248018296[21] = 0.0;
   out_1571472922248018296[22] = 0.0;
   out_1571472922248018296[23] = 0.0;
   out_1571472922248018296[24] = 0.0;
   out_1571472922248018296[25] = 0.0;
   out_1571472922248018296[26] = 0.0;
   out_1571472922248018296[27] = 0.0;
   out_1571472922248018296[28] = 0.0;
   out_1571472922248018296[29] = 0.0;
   out_1571472922248018296[30] = 1.0;
   out_1571472922248018296[31] = 0.0;
   out_1571472922248018296[32] = 0.0;
   out_1571472922248018296[33] = 0.0;
   out_1571472922248018296[34] = 0.0;
   out_1571472922248018296[35] = 0.0;
   out_1571472922248018296[36] = 0.0;
   out_1571472922248018296[37] = 0.0;
   out_1571472922248018296[38] = 0.0;
   out_1571472922248018296[39] = 0.0;
   out_1571472922248018296[40] = 1.0;
   out_1571472922248018296[41] = 0.0;
   out_1571472922248018296[42] = 0.0;
   out_1571472922248018296[43] = 0.0;
   out_1571472922248018296[44] = 0.0;
   out_1571472922248018296[45] = 0.0;
   out_1571472922248018296[46] = 0.0;
   out_1571472922248018296[47] = 0.0;
   out_1571472922248018296[48] = 0.0;
   out_1571472922248018296[49] = 0.0;
   out_1571472922248018296[50] = 1.0;
   out_1571472922248018296[51] = 0.0;
   out_1571472922248018296[52] = 0.0;
   out_1571472922248018296[53] = 0.0;
   out_1571472922248018296[54] = 0.0;
   out_1571472922248018296[55] = 0.0;
   out_1571472922248018296[56] = 0.0;
   out_1571472922248018296[57] = 0.0;
   out_1571472922248018296[58] = 0.0;
   out_1571472922248018296[59] = 0.0;
   out_1571472922248018296[60] = 1.0;
   out_1571472922248018296[61] = 0.0;
   out_1571472922248018296[62] = 0.0;
   out_1571472922248018296[63] = 0.0;
   out_1571472922248018296[64] = 0.0;
   out_1571472922248018296[65] = 0.0;
   out_1571472922248018296[66] = 0.0;
   out_1571472922248018296[67] = 0.0;
   out_1571472922248018296[68] = 0.0;
   out_1571472922248018296[69] = 0.0;
   out_1571472922248018296[70] = 1.0;
   out_1571472922248018296[71] = 0.0;
   out_1571472922248018296[72] = 0.0;
   out_1571472922248018296[73] = 0.0;
   out_1571472922248018296[74] = 0.0;
   out_1571472922248018296[75] = 0.0;
   out_1571472922248018296[76] = 0.0;
   out_1571472922248018296[77] = 0.0;
   out_1571472922248018296[78] = 0.0;
   out_1571472922248018296[79] = 0.0;
   out_1571472922248018296[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_3070664500164102760) {
   out_3070664500164102760[0] = state[0];
   out_3070664500164102760[1] = state[1];
   out_3070664500164102760[2] = state[2];
   out_3070664500164102760[3] = state[3];
   out_3070664500164102760[4] = state[4];
   out_3070664500164102760[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_3070664500164102760[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_3070664500164102760[7] = state[7];
   out_3070664500164102760[8] = state[8];
}
void F_fun(double *state, double dt, double *out_2365857006052744488) {
   out_2365857006052744488[0] = 1;
   out_2365857006052744488[1] = 0;
   out_2365857006052744488[2] = 0;
   out_2365857006052744488[3] = 0;
   out_2365857006052744488[4] = 0;
   out_2365857006052744488[5] = 0;
   out_2365857006052744488[6] = 0;
   out_2365857006052744488[7] = 0;
   out_2365857006052744488[8] = 0;
   out_2365857006052744488[9] = 0;
   out_2365857006052744488[10] = 1;
   out_2365857006052744488[11] = 0;
   out_2365857006052744488[12] = 0;
   out_2365857006052744488[13] = 0;
   out_2365857006052744488[14] = 0;
   out_2365857006052744488[15] = 0;
   out_2365857006052744488[16] = 0;
   out_2365857006052744488[17] = 0;
   out_2365857006052744488[18] = 0;
   out_2365857006052744488[19] = 0;
   out_2365857006052744488[20] = 1;
   out_2365857006052744488[21] = 0;
   out_2365857006052744488[22] = 0;
   out_2365857006052744488[23] = 0;
   out_2365857006052744488[24] = 0;
   out_2365857006052744488[25] = 0;
   out_2365857006052744488[26] = 0;
   out_2365857006052744488[27] = 0;
   out_2365857006052744488[28] = 0;
   out_2365857006052744488[29] = 0;
   out_2365857006052744488[30] = 1;
   out_2365857006052744488[31] = 0;
   out_2365857006052744488[32] = 0;
   out_2365857006052744488[33] = 0;
   out_2365857006052744488[34] = 0;
   out_2365857006052744488[35] = 0;
   out_2365857006052744488[36] = 0;
   out_2365857006052744488[37] = 0;
   out_2365857006052744488[38] = 0;
   out_2365857006052744488[39] = 0;
   out_2365857006052744488[40] = 1;
   out_2365857006052744488[41] = 0;
   out_2365857006052744488[42] = 0;
   out_2365857006052744488[43] = 0;
   out_2365857006052744488[44] = 0;
   out_2365857006052744488[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_2365857006052744488[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_2365857006052744488[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2365857006052744488[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2365857006052744488[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_2365857006052744488[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_2365857006052744488[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_2365857006052744488[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_2365857006052744488[53] = -9.8100000000000005*dt;
   out_2365857006052744488[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_2365857006052744488[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_2365857006052744488[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2365857006052744488[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2365857006052744488[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_2365857006052744488[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_2365857006052744488[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_2365857006052744488[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2365857006052744488[62] = 0;
   out_2365857006052744488[63] = 0;
   out_2365857006052744488[64] = 0;
   out_2365857006052744488[65] = 0;
   out_2365857006052744488[66] = 0;
   out_2365857006052744488[67] = 0;
   out_2365857006052744488[68] = 0;
   out_2365857006052744488[69] = 0;
   out_2365857006052744488[70] = 1;
   out_2365857006052744488[71] = 0;
   out_2365857006052744488[72] = 0;
   out_2365857006052744488[73] = 0;
   out_2365857006052744488[74] = 0;
   out_2365857006052744488[75] = 0;
   out_2365857006052744488[76] = 0;
   out_2365857006052744488[77] = 0;
   out_2365857006052744488[78] = 0;
   out_2365857006052744488[79] = 0;
   out_2365857006052744488[80] = 1;
}
void h_25(double *state, double *unused, double *out_7208997417211176832) {
   out_7208997417211176832[0] = state[6];
}
void H_25(double *state, double *unused, double *out_3987544096248591949) {
   out_3987544096248591949[0] = 0;
   out_3987544096248591949[1] = 0;
   out_3987544096248591949[2] = 0;
   out_3987544096248591949[3] = 0;
   out_3987544096248591949[4] = 0;
   out_3987544096248591949[5] = 0;
   out_3987544096248591949[6] = 1;
   out_3987544096248591949[7] = 0;
   out_3987544096248591949[8] = 0;
}
void h_24(double *state, double *unused, double *out_7481715524482624299) {
   out_7481715524482624299[0] = state[4];
   out_7481715524482624299[1] = state[5];
}
void H_24(double *state, double *unused, double *out_1810329672641441976) {
   out_1810329672641441976[0] = 0;
   out_1810329672641441976[1] = 0;
   out_1810329672641441976[2] = 0;
   out_1810329672641441976[3] = 0;
   out_1810329672641441976[4] = 1;
   out_1810329672641441976[5] = 0;
   out_1810329672641441976[6] = 0;
   out_1810329672641441976[7] = 0;
   out_1810329672641441976[8] = 0;
   out_1810329672641441976[9] = 0;
   out_1810329672641441976[10] = 0;
   out_1810329672641441976[11] = 0;
   out_1810329672641441976[12] = 0;
   out_1810329672641441976[13] = 0;
   out_1810329672641441976[14] = 1;
   out_1810329672641441976[15] = 0;
   out_1810329672641441976[16] = 0;
   out_1810329672641441976[17] = 0;
}
void h_30(double *state, double *unused, double *out_438162190860825896) {
   out_438162190860825896[0] = state[4];
}
void H_30(double *state, double *unused, double *out_1469211137741343322) {
   out_1469211137741343322[0] = 0;
   out_1469211137741343322[1] = 0;
   out_1469211137741343322[2] = 0;
   out_1469211137741343322[3] = 0;
   out_1469211137741343322[4] = 1;
   out_1469211137741343322[5] = 0;
   out_1469211137741343322[6] = 0;
   out_1469211137741343322[7] = 0;
   out_1469211137741343322[8] = 0;
}
void h_26(double *state, double *unused, double *out_4563511076800019749) {
   out_4563511076800019749[0] = state[7];
}
void H_26(double *state, double *unused, double *out_7729047415122648173) {
   out_7729047415122648173[0] = 0;
   out_7729047415122648173[1] = 0;
   out_7729047415122648173[2] = 0;
   out_7729047415122648173[3] = 0;
   out_7729047415122648173[4] = 0;
   out_7729047415122648173[5] = 0;
   out_7729047415122648173[6] = 0;
   out_7729047415122648173[7] = 1;
   out_7729047415122648173[8] = 0;
}
void h_27(double *state, double *unused, double *out_6265487564309514397) {
   out_6265487564309514397[0] = state[3];
}
void H_27(double *state, double *unused, double *out_3643974449541768233) {
   out_3643974449541768233[0] = 0;
   out_3643974449541768233[1] = 0;
   out_3643974449541768233[2] = 0;
   out_3643974449541768233[3] = 1;
   out_3643974449541768233[4] = 0;
   out_3643974449541768233[5] = 0;
   out_3643974449541768233[6] = 0;
   out_3643974449541768233[7] = 0;
   out_3643974449541768233[8] = 0;
}
void h_29(double *state, double *unused, double *out_6316447678419540984) {
   out_6316447678419540984[0] = state[1];
}
void H_29(double *state, double *unused, double *out_958979793426951138) {
   out_958979793426951138[0] = 0;
   out_958979793426951138[1] = 1;
   out_958979793426951138[2] = 0;
   out_958979793426951138[3] = 0;
   out_958979793426951138[4] = 0;
   out_958979793426951138[5] = 0;
   out_958979793426951138[6] = 0;
   out_958979793426951138[7] = 0;
   out_958979793426951138[8] = 0;
}
void h_28(double *state, double *unused, double *out_3384947045134040079) {
   out_3384947045134040079[0] = state[0];
}
void H_28(double *state, double *unused, double *out_6041378810496481712) {
   out_6041378810496481712[0] = 1;
   out_6041378810496481712[1] = 0;
   out_6041378810496481712[2] = 0;
   out_6041378810496481712[3] = 0;
   out_6041378810496481712[4] = 0;
   out_6041378810496481712[5] = 0;
   out_6041378810496481712[6] = 0;
   out_6041378810496481712[7] = 0;
   out_6041378810496481712[8] = 0;
}
void h_31(double *state, double *unused, double *out_2597869179779832900) {
   out_2597869179779832900[0] = state[8];
}
void H_31(double *state, double *unused, double *out_8355255517355999649) {
   out_8355255517355999649[0] = 0;
   out_8355255517355999649[1] = 0;
   out_8355255517355999649[2] = 0;
   out_8355255517355999649[3] = 0;
   out_8355255517355999649[4] = 0;
   out_8355255517355999649[5] = 0;
   out_8355255517355999649[6] = 0;
   out_8355255517355999649[7] = 0;
   out_8355255517355999649[8] = 1;
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

void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_25, H_25, NULL, in_z, in_R, in_ea, MAHA_THRESH_25);
}
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<2, 3, 0>(in_x, in_P, h_24, H_24, NULL, in_z, in_R, in_ea, MAHA_THRESH_24);
}
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_30, H_30, NULL, in_z, in_R, in_ea, MAHA_THRESH_30);
}
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_26, H_26, NULL, in_z, in_R, in_ea, MAHA_THRESH_26);
}
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_27, H_27, NULL, in_z, in_R, in_ea, MAHA_THRESH_27);
}
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_29, H_29, NULL, in_z, in_R, in_ea, MAHA_THRESH_29);
}
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_28, H_28, NULL, in_z, in_R, in_ea, MAHA_THRESH_28);
}
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_31, H_31, NULL, in_z, in_R, in_ea, MAHA_THRESH_31);
}
void car_err_fun(double *nom_x, double *delta_x, double *out_1976458697034392713) {
  err_fun(nom_x, delta_x, out_1976458697034392713);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_8774680380747325588) {
  inv_err_fun(nom_x, true_x, out_8774680380747325588);
}
void car_H_mod_fun(double *state, double *out_1571472922248018296) {
  H_mod_fun(state, out_1571472922248018296);
}
void car_f_fun(double *state, double dt, double *out_3070664500164102760) {
  f_fun(state,  dt, out_3070664500164102760);
}
void car_F_fun(double *state, double dt, double *out_2365857006052744488) {
  F_fun(state,  dt, out_2365857006052744488);
}
void car_h_25(double *state, double *unused, double *out_7208997417211176832) {
  h_25(state, unused, out_7208997417211176832);
}
void car_H_25(double *state, double *unused, double *out_3987544096248591949) {
  H_25(state, unused, out_3987544096248591949);
}
void car_h_24(double *state, double *unused, double *out_7481715524482624299) {
  h_24(state, unused, out_7481715524482624299);
}
void car_H_24(double *state, double *unused, double *out_1810329672641441976) {
  H_24(state, unused, out_1810329672641441976);
}
void car_h_30(double *state, double *unused, double *out_438162190860825896) {
  h_30(state, unused, out_438162190860825896);
}
void car_H_30(double *state, double *unused, double *out_1469211137741343322) {
  H_30(state, unused, out_1469211137741343322);
}
void car_h_26(double *state, double *unused, double *out_4563511076800019749) {
  h_26(state, unused, out_4563511076800019749);
}
void car_H_26(double *state, double *unused, double *out_7729047415122648173) {
  H_26(state, unused, out_7729047415122648173);
}
void car_h_27(double *state, double *unused, double *out_6265487564309514397) {
  h_27(state, unused, out_6265487564309514397);
}
void car_H_27(double *state, double *unused, double *out_3643974449541768233) {
  H_27(state, unused, out_3643974449541768233);
}
void car_h_29(double *state, double *unused, double *out_6316447678419540984) {
  h_29(state, unused, out_6316447678419540984);
}
void car_H_29(double *state, double *unused, double *out_958979793426951138) {
  H_29(state, unused, out_958979793426951138);
}
void car_h_28(double *state, double *unused, double *out_3384947045134040079) {
  h_28(state, unused, out_3384947045134040079);
}
void car_H_28(double *state, double *unused, double *out_6041378810496481712) {
  H_28(state, unused, out_6041378810496481712);
}
void car_h_31(double *state, double *unused, double *out_2597869179779832900) {
  h_31(state, unused, out_2597869179779832900);
}
void car_H_31(double *state, double *unused, double *out_8355255517355999649) {
  H_31(state, unused, out_8355255517355999649);
}
void car_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
void car_set_mass(double x) {
  set_mass(x);
}
void car_set_rotational_inertia(double x) {
  set_rotational_inertia(x);
}
void car_set_center_to_front(double x) {
  set_center_to_front(x);
}
void car_set_center_to_rear(double x) {
  set_center_to_rear(x);
}
void car_set_stiffness_front(double x) {
  set_stiffness_front(x);
}
void car_set_stiffness_rear(double x) {
  set_stiffness_rear(x);
}
}

const EKF car = {
  .name = "car",
  .kinds = { 25, 24, 30, 26, 27, 29, 28, 31 },
  .feature_kinds = {  },
  .f_fun = car_f_fun,
  .F_fun = car_F_fun,
  .err_fun = car_err_fun,
  .inv_err_fun = car_inv_err_fun,
  .H_mod_fun = car_H_mod_fun,
  .predict = car_predict,
  .hs = {
    { 25, car_h_25 },
    { 24, car_h_24 },
    { 30, car_h_30 },
    { 26, car_h_26 },
    { 27, car_h_27 },
    { 29, car_h_29 },
    { 28, car_h_28 },
    { 31, car_h_31 },
  },
  .Hs = {
    { 25, car_H_25 },
    { 24, car_H_24 },
    { 30, car_H_30 },
    { 26, car_H_26 },
    { 27, car_H_27 },
    { 29, car_H_29 },
    { 28, car_H_28 },
    { 31, car_H_31 },
  },
  .updates = {
    { 25, car_update_25 },
    { 24, car_update_24 },
    { 30, car_update_30 },
    { 26, car_update_26 },
    { 27, car_update_27 },
    { 29, car_update_29 },
    { 28, car_update_28 },
    { 31, car_update_31 },
  },
  .Hes = {
  },
  .sets = {
    { "mass", car_set_mass },
    { "rotational_inertia", car_set_rotational_inertia },
    { "center_to_front", car_set_center_to_front },
    { "center_to_rear", car_set_center_to_rear },
    { "stiffness_front", car_set_stiffness_front },
    { "stiffness_rear", car_set_stiffness_rear },
  },
  .extra_routines = {
  },
};

ekf_lib_init(car)
