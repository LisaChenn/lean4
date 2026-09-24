// Lean compiler output
// Module: Lean4.Q8
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
LEAN_EXPORT lean_object* lp_Lean4_q8_acres;
LEAN_EXPORT lean_object* lp_Lean4_q8_tonsPerAcre;
LEAN_EXPORT lean_object* lp_Lean4_q8_barrelsPerTon;
LEAN_EXPORT lean_object* lp_Lean4_q8_barrelsPerYear;
static lean_object* _init_lp_Lean4_q8_acres(void){
_start:
{
lean_object* v___x_1_; 
v___x_1_ = lean_unsigned_to_nat(10u);
return v___x_1_;
}
}
static lean_object* _init_lp_Lean4_q8_tonsPerAcre(void){
_start:
{
lean_object* v___x_2_; 
v___x_2_ = lean_unsigned_to_nat(5u);
return v___x_2_;
}
}
static lean_object* _init_lp_Lean4_q8_barrelsPerTon(void){
_start:
{
lean_object* v___x_3_; 
v___x_3_ = lean_unsigned_to_nat(2u);
return v___x_3_;
}
}
static lean_object* _init_lp_Lean4_q8_barrelsPerYear(void){
_start:
{
lean_object* v___x_4_; 
v___x_4_ = lean_unsigned_to_nat(100u);
return v___x_4_;
}
}
lean_object* initialize_Init(uint8_t builtin);
lean_object* initialize_Init(uint8_t builtin);
lean_object* initialize_mathlib_Mathlib_Tactic(uint8_t builtin);
void lean_initialize();
static bool _G_initialized = false;
LEAN_EXPORT lean_object* initialize_Lean4_Lean4_Q8(uint8_t builtin) {
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
lp_Lean4_q8_acres = _init_lp_Lean4_q8_acres();
lean_mark_persistent(lp_Lean4_q8_acres);
lp_Lean4_q8_tonsPerAcre = _init_lp_Lean4_q8_tonsPerAcre();
lean_mark_persistent(lp_Lean4_q8_tonsPerAcre);
lp_Lean4_q8_barrelsPerTon = _init_lp_Lean4_q8_barrelsPerTon();
lean_mark_persistent(lp_Lean4_q8_barrelsPerTon);
lp_Lean4_q8_barrelsPerYear = _init_lp_Lean4_q8_barrelsPerYear();
lean_mark_persistent(lp_Lean4_q8_barrelsPerYear);
return lean_io_result_mk_ok(lean_box(0));
}
#ifdef __cplusplus
}
#endif
