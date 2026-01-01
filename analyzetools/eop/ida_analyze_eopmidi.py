"""
IDA Pro Analysis Script for EOPmidi.exe
Target: Analyze EOP timing encoding algorithm

Run with:
  idat.exe -A -S"ida_analyze_eopmidi.py" "D:\dw11\EveryonePiano\EOPmidi.exe"
"""

import idc
import idaapi
import idautils

# Output file
OUTPUT = r"D:\dw11\analyzetools\eopmidi_analysis.txt"

def log(msg):
    print(msg)
    with open(OUTPUT, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def analyze_marker_byte_refs():
    """Find functions that compare against marker bytes (0xE2, 0xE6, 0xF2, 0xF6)"""
    log("\n=== Marker Byte Analysis ===")

    marker_bytes = [0xE2, 0xE6, 0xF2, 0xF6, 0xBD, 0xD8, 0xDE, 0xF4]
    found_funcs = set()

    # Search for immediate values
    for mb in marker_bytes:
        log(f"\n[Searching for 0x{mb:02X}]")

        # Search in code segments
        for seg_ea in idautils.Segments():
            seg = idaapi.getseg(seg_ea)
            if seg.type != idaapi.SEG_CODE:
                continue

            ea = seg.start_ea
            while ea < seg.end_ea:
                # Check if instruction uses this immediate
                insn = idaapi.insn_t()
                if idaapi.decode_insn(insn, ea) > 0:
                    for op in insn.ops:
                        if op.type == idaapi.o_imm and op.value == mb:
                            func = idaapi.get_func(ea)
                            func_name = idc.get_func_name(ea) if func else "no_func"
                            func_ea = func.start_ea if func else 0

                            disasm = idc.GetDisasm(ea)
                            log(f"  0x{ea:08X} in {func_name}: {disasm}")
                            found_funcs.add(func_ea)
                            break
                ea = idc.next_head(ea)

    log(f"\n[Found {len(found_funcs)} functions using marker bytes]")
    return found_funcs

def analyze_midi_functions():
    """Find MIDI-related functions"""
    log("\n=== MIDI Function Analysis ===")

    midi_imports = ["midiOutOpen", "midiOutShortMsg", "midiOutClose",
                    "midiInOpen", "midiInStart", "midiInClose"]

    for name in midi_imports:
        ea = idc.get_name_ea_simple(name)
        if ea != idc.BADADDR:
            log(f"\n[{name} @ 0x{ea:08X}]")

            # Find cross-references
            for xref in idautils.XrefsTo(ea):
                caller_func = idaapi.get_func(xref.frm)
                if caller_func:
                    log(f"  Called from: {idc.get_func_name(xref.frm)} @ 0x{xref.frm:08X}")

def analyze_file_operations():
    """Find file read operations (potential EOP parsing)"""
    log("\n=== File Operation Analysis ===")

    file_funcs = ["CreateFileW", "CreateFileA", "ReadFile", "fread", "fopen"]

    for name in file_funcs:
        ea = idc.get_name_ea_simple(name)
        if ea != idc.BADADDR:
            log(f"\n[{name} @ 0x{ea:08X}]")

            xrefs = list(idautils.XrefsTo(ea))
            log(f"  {len(xrefs)} call sites")

            for xref in xrefs[:5]:  # First 5 callers
                caller_func = idaapi.get_func(xref.frm)
                if caller_func:
                    log(f"  - {idc.get_func_name(xref.frm)} @ 0x{xref.frm:08X}")

def find_string_refs():
    """Find references to .eop and .mid strings"""
    log("\n=== String Reference Analysis ===")

    patterns = [".eop", ".mid", "midi", "note", "tempo", "time"]

    for seg_ea in idautils.Segments():
        seg = idaapi.getseg(seg_ea)
        if seg.type != idaapi.SEG_DATA:
            continue

        ea = seg.start_ea
        while ea < seg.end_ea:
            s = idc.get_strlit_contents(ea)
            if s:
                try:
                    s_str = s.decode('utf-8', errors='ignore').lower()
                    for p in patterns:
                        if p in s_str:
                            log(f"  0x{ea:08X}: \"{s.decode('utf-8', errors='ignore')}\"")

                            # Find xrefs to this string
                            for xref in idautils.XrefsTo(ea):
                                func = idaapi.get_func(xref.frm)
                                if func:
                                    log(f"    -> {idc.get_func_name(xref.frm)} @ 0x{xref.frm:08X}")
                            break
                except:
                    pass
            ea = idc.next_head(ea)

def analyze_key_function(ea):
    """Analyze a specific function for timing logic"""
    func = idaapi.get_func(ea)
    if not func:
        return

    log(f"\n=== Function Analysis: {idc.get_func_name(ea)} @ 0x{ea:08X} ===")
    log(f"  Size: {func.end_ea - func.start_ea} bytes")

    # Decompile if Hex-Rays available
    try:
        cfunc = idaapi.decompile(ea)
        if cfunc:
            log(f"\n  [Decompiled pseudocode]")
            log(str(cfunc))
    except:
        log("  [Decompilation not available]")

def main():
    # Clear output file
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("EOPmidi.exe Analysis Report\n")
        f.write("=" * 50 + "\n")

    log(f"Analyzing: {idc.get_input_file_path()}")
    log(f"Base: 0x{idaapi.get_imagebase():08X}")

    # Wait for auto-analysis
    idaapi.auto_wait()

    # Run analyses
    find_string_refs()
    analyze_file_operations()
    analyze_midi_functions()
    marker_funcs = analyze_marker_byte_refs()

    # Analyze key functions
    if marker_funcs:
        log("\n=== Key Function Details ===")
        for func_ea in sorted(marker_funcs)[:5]:  # Top 5
            if func_ea:
                analyze_key_function(func_ea)

    log("\n=== Analysis Complete ===")

    # Exit IDA
    idc.qexit(0)

if __name__ == "__main__":
    main()
