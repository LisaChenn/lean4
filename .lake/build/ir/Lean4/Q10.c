// Lean compiler output
// Module: Lean4.Q10
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
LEAN_EXPORT lean_object* lp_Lean4_q10_blueBlocks;
LEAN_EXPORT lean_object* lp_Lean4_q10_yellowBlocks;
LEAN_EXPORT lean_object* lp_Lean4_q10_totalBlocks;
LEAN_EXPORT lean_object* lp_Lean4_q10_redBlocks;
static lean_object* _init_lp_Lean4_q10_blueBlocks(void){
_start:
{
lean_object* v___x_1_; 
v___x_1_ = lean_unsigned_to_nat(4u);
return v___x_1_;
}
}
static lean_object* _init_lp_Lean4_q10_yellowBlocks(void){
_start:
{
lean_object* v___x_2_; 
v___x_2_ = lean_unsigned_to_nat(8u);
return v___x_2_;
}
}
static lean_object* _init_lp_Lean4_q10_totalBlocks(void){
_start:
{
lean_object* v___x_3_; 
v___x_3_ = lean_unsigned_to_nat(32u);
return v___x_3_;
}
}
static lean_object* _init_lp_Lean4_q10_redBlocks(void){
_start:
{
lean_object* v___x_4_; 
v___x_4_ = lean_unsigned_to_nat(20u);
return v___x_4_;
}
}
lean_object* initialize_Init(uint8_t builtin);
lean_object* initialize_Init(uint8_t builtin);
lean_object* initialize_mathlib_Mathlib_Tactic(uint8_t builtin);
void lean_initialize();
static bool _G_initialized = false;
LEAN_EXPORT lean_object* initialize_Lean4_Lean4_Q10(uint8_t builtin) {
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
lp_Lean4_q10_blueBlocks = _init_lp_Lean4_q10_blueBlocks();
lean_mark_persistent(lp_Lean4_q10_blueBlocks);
lp_Lean4_q10_yellowBlocks = _init_lp_Lean4_q10_yellowBlocks();
lean_mark_persistent(lp_Lean4_q10_yellowBlocks);
lp_Lean4_q10_totalBlocks = _init_lp_Lean4_q10_totalBlocks();
lean_mark_persistent(lp_Lean4_q10_totalBlocks);
lp_Lean4_q10_redBlocks = _init_lp_Lean4_q10_redBlocks();
lean_mark_persistent(lp_Lean4_q10_redBlocks);
return lean_io_result_mk_ok(lean_box(0));
}
#ifdef __cplusplus
}
#endif
