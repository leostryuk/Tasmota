#include "be_constobj.h"

static be_define_const_map_slots(be_class_lv_style_map) {
    { be_const_key(init, -1), be_const_func(lvs_init) },
    { be_const_key(tostring, -1), be_const_func(lvs_tostring) },
    { be_const_key(_p, -1), be_const_var(0) },
    { be_const_key(member, 0), be_const_func(lvx_member) },
};

static be_define_const_map(
    be_class_lv_style_map,
    4
);

BE_EXPORT_VARIABLE be_define_const_class(
    be_class_lv_style,
    1,
    NULL,
    lv_style
);
