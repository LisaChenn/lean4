// Lean compiler output
// Module: Lean4.Q9
// Imports: public import Init public meta import Init public import Mathlib.Tactic
#include <lean/lean.h>
#if defined(__clang__)
#pragma clang diagnostic ignored "-Wunused-parameter"
#pragma clang diagnostic ignored "-Wunused-label"
#elif defined(__GNUC__) && !defined(__CLANG__)
#pragma GCC diagnostic ignored "-Wunused-parameter"
#pragma GCC diagnostic ignored "-Wunused-label"
#pragma GCC diagnostic ignored "-Wunused-but-set-variable"
#endif
#ifdef __cplusplus
extern "C" {
#endif
LEAN_EXPORT lean_object* lp_Lean4_q9_charlieFriends;
LEAN_EXPORT lean_object* lp_Lean4_q9_dorothyFriends;
LEAN_EXPORT lean_object* lp_Lean4_q9_jamesFriends;
static lean_object* _init_lp_Lean4_q9_charlieFriends(void){
_start:
{
lean_object* v___x_1_; 
v___x_1_ = lean_unsigned_to_nat(12u);
return v___x_1_;
}
}
static lean_object* _init_lp_Lean4_q9_dorothyFriends(void){
_start:
{
lean_object* v___x_2_; 
v___x_2_ = lean_unsigned_to_nat(4u);
return v___x_2_;
}
}
static lean_object* _init_lp_Lean4_q9_jamesFriends(void){
_start:
{
lean_object* v___x_3_; 
v___x_3_ = lean_unsigned_to_nat(16u);
return v___x_3_;
}
}
lean_object* initialize_Init(uint8_t builtin);
lean_object* initialize_Init(uint8_t builtin);
lean_object* initialize_mathlib_Mathlib_Tactic(uint8_t builtin);
void lean_initialize();
static bool _G_initialized = false;
LEAN_EXPORT lean_object* initialize_Lean4_Lean4_Q9(uint8_t builtin) {
lean_object * res;
if (_G_initialized) return lean_io_result_mk_ok(lean_box(0));
_G_initialized = true;
lean_initialize();
res = initialize_Init(builtin);
if (lean_io_result_is_error(res)) return res;
lean_dec_ref(res);
res = initialize_Init(builtin);
if (lean_io_result_is_error(res)) return res;
lean_dec_ref(res);
res = initialize_mathlib_Mathlib_Tactic(builtin);
if (lean_io_result_is_error(res)) return res;
lean_dec_ref(res);
lp_Lean4_q9_charlieFriends = _init_lp_Lean4_q9_charlieFriends();
lean_mark_persistent(lp_Lean4_q9_charlieFriends);
lp_Lean4_q9_dorothyFriends = _init_lp_Lean4_q9_dorothyFriends();
lean_mark_persistent(lp_Lean4_q9_dorothyFriends);
lp_Lean4_q9_jamesFriends = _init_lp_Lean4_q9_jamesFriends();
lean_mark_persistent(lp_Lean4_q9_jamesFriends);
return lean_io_result_mk_ok(lean_box(0));
}
#ifdef __cplusplus
}
#endif
