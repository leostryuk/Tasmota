import re
import sys
import glob

# https://stackoverflow.com/a/241506
def comment_remover(text):
    def replacer(match):
        s = match.group(0)
        if s.startswith('/'):
            return " " # note: a space and not an empty string
        else:
            return s
    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )
    return re.sub(pattern, replacer, text)

# compute a sorted list of files from a prefix and a list of glob patterns
def list_files(prefix, glob_list):
  r = []
  for g in glob_list:
    r += glob.glob(prefix + g, recursive=True)
  return sorted(r)

def clean_source(raw):
  raw = comment_remover(raw)    # remove comments
  # convert cr/lf or cr to lf
  raw = re.sub('\r\n ', '\n', raw)
  raw = re.sub('\r', '\n', raw)
  # group multilines into a single line, i.e. if line ends with '\', put in a single line
  raw = re.sub('\\\\\n', ' ', raw)
  # remove preprocessor directives
  raw = re.sub('\n[ \t]*#[^\n]*(?=\n)', '', raw)
  raw = re.sub('^[ \t]*#[^\n]*\n', '', raw)
  raw = re.sub('\n[ \t]*#[^\n]*$', '', raw)

  # remove extern "C" {}
  raw = re.sub('extern\s+"C"\s+{(.*)}', '\\1', raw, flags=re.DOTALL)

  # remove empty lines
  raw = re.sub('\n[ \t]*(?=\n)', '', raw)
  raw = re.sub('^[ \t]*\n', '', raw)  # remove first empty line
  raw = re.sub('\n[ \t]*$', '', raw)  # remove last empty line
  return raw

# ################################################################################
# Parse function signatures
# ################################################################################

lv_src_prefix = "../../lib/libesp32_lvgl/LVGL8/src/"
lv_fun_globs = [ 
                  "widgets/*.h",   # all widgets
                  # "extra/widgets/*/*.h",
                  "extra/widgets/chart/*.h",
                  "extra/widgets/colorwheel/*.h",
                  "extra/widgets/imgbtn/*.h",
                  "extra/widgets/led/*.h",
                  "extra/widgets/meter/*.h",
                  "extra/widgets/msgbox/*.h",
                  "extra/widgets/spinbox/*.h",
                  "core/*.h",
                  "draw/*.h",
                  "misc/lv_style_gen.h",
                  #"misc/lv_area.h",
                  #"**/*.h",
              ]
headers_names = list_files(lv_src_prefix, lv_fun_globs)
# headers_names += ["lv_pre_style.h"] # for LVGL v7, add pre-generated style functions from C preprocessor

# unit test
# headers_names = [ '../../lib/libesp32_lvgl/LVGL/src/lv_widgets/lv_btn.h' ]
# headers_names = [ '../../lib/libesp32_lvgl/LVGL/src/lv_api_map.h' ]

output_filename = "lv_funcs.h"
sys.stdout = open(output_filename, 'w')

print("""
// Automatically generated from LVGL source with `python3 preprocessor.py`
// Extract function signatures from LVGL APIs in headers

// Custom Tasmota functions
void lv_img_set_tasmota_logo(lv_obj_t * img);

// ======================================================================
// Artificial
// ======================================================================

lv_color_t lv_color_mix(lv_color_t c1, lv_color_t c2, uint8_t mix);

// ======================================================================
// LV top level functions
// ======================================================================

// resolution
lv_coord_t lv_get_hor_res(void);
lv_coord_t lv_get_ver_res(void);

// layers
//static inline lv_obj_t * lv_layer_sys(void);
//static inline lv_obj_t * lv_layer_top(void);

// ======================================================================
// Generated from headers
// ======================================================================

""")

for header_name in headers_names:
  with open(header_name) as f:
    print("// " + header_name)
    raw = clean_source(f.read())

    # remove anything in '{' '}'
    while True:
      (raw, repl) = re.subn('\{[^{]*?\}', ';', raw, flags=re.DOTALL)  # replace with ';' to make pattern matching still work
      if (repl == 0): break  # no more replace, stop

    raw_f = re.findall('(^|;|})\s*([^;{}]+\(.*?\))\s*(?=(;|{))', raw, flags=re.DOTALL)
    fun_defs = [ x[1] for x in raw_f]
    # remove any CRLF or multi-space
    fun_defs = [ re.sub('[ \t\r\n]+', ' ', x) for x in fun_defs]

    # parse individual
    for fun in fun_defs:
      # remove LV_ATTRIBUTE_FAST_MEM 
      fun = re.sub('LV_ATTRIBUTE_FAST_MEM ', '', fun)
      exclude = False
      for exclude_prefix in ["typedef", "_LV_", "LV_"]:
        if fun.startswith(exclude_prefix): exclude = True
      if exclude: continue

      # extrac the function name
      fun_name = re.search('\s(\w+)\([^\(]*$', fun)
      if fun_name != None:
        fun_name = fun_name.group(1)    # we now have the function name
        
        # exclude specific names
        for exclude_pattern in [
              "^_",    # skip if function name starts with '_'
              "^lv_debug",    # all debug functions
              "^lv_init", "^lv_deinit",
              "^lv_templ_",
              "^lv_imgbtn_get_src_",    # LV_IMGBTN_TILED == 0
              "^lv_imgbtn_set_src_tiled",# !LV_IMGBTN_TILED
              "^lv_disp_",
              "^lv_refr_get_fps_",      # no LV_USE_PERF_MONITOR
              "^lv_img_cache_",
              "^lv_img_decoder_",
              "^lv_img_cf_",
              "^lv_img_buf_",
              "^lv_indev_scroll_",
              "^lv_keyboard_def_event_cb",  # need to fix conditional include
              "^lv_event_get_",            # event_getters not needed
            ]:
          if re.search(exclude_pattern, fun_name): exclude = True
        if exclude: continue
      
      print(fun)
  print()

sys.stdout.close()

# ################################################################################
# Parse 'enum'
# ################################################################################

lv_src_prefix = "../../lib/libesp32_lvgl/LVGL8/src/"
lv_fun_globs = [ "**/*.h" ]
headers_names = list_files(lv_src_prefix, lv_fun_globs)

output_filename = "lv_enum.h"
sys.stdout = open(output_filename, 'w')
print("""
// LV Colors - we store in 24 bits format and will convert at runtime
// This is specific treatment because we keep colors in 24 bits format
COLOR_WHITE=0xFFFFFF
COLOR_SILVER=0xC0C0C0
COLOR_GRAY=0x808080
COLOR_BLACK=0x000000
COLOR_RED=0xFF0000
COLOR_MAROON=0x800000
COLOR_YELLOW=0xFFFF00
COLOR_OLIVE=0x808000
COLOR_LIME=0x00FF00
COLOR_GREEN=0x008000
COLOR_CYAN=0x00FFFF
COLOR_AQUA=0x00FFFF
COLOR_TEAL=0x008080
COLOR_BLUE=0x0000FF
COLOR_NAVY=0x000080
COLOR_MAGENTA=0xFF00FF
COLOR_PURPLE=0x800080

// following are #define, not enum
LV_RADIUS_CIRCLE
LV_TEXTAREA_CURSOR_LAST
LV_STYLE_PROP_ANY

LV_SIZE_CONTENT
""")



for header_name in headers_names:
  with open(header_name) as f:
    raw = clean_source(f.read())

    # extract enums
    enums = re.findall('enum\s+{(.*?)}', raw, flags=re.DOTALL)
    for enum in enums:  # iterate on all matches
      # remove enums defined via a macro
      enum = re.sub('\S+\((.*?),.*?\),', '\\1,', enum)  # turn 'LV_STYLE_PROP_INIT(LV_STYLE_SIZE, 0x0, LV_STYLE_ID_VALUE + 3, LV_STYLE_ATTR_NONE),' into 'LV_STYLE_SIZE'
      #
      enum_elt = enum.split(",")
      for enum_item in enum_elt:
        # remove any space
        enum_item = re.sub('[ \t\n]', '', enum_item)
        # remove anything after '='
        enum_item = re.sub('=.*$', '', enum_item)

        # item is ready
        exclude = False
        for exclude_prefix in ["_", "LV_BIDI_DIR_", "LV_FONT_", "LV_IMG_CF_RESERVED_", "LV_IMG_CF_USER_",
                               "LV_SIGNAL_", "LV_TEMPL_", "LV_TASK_PRIO_", "LV_THEME_", "LV_KEYBOARD_"]:
          if enum_item.startswith(exclude_prefix): exclude = True
        if exclude: continue

        print(enum_item)
sys.stdout.close()
