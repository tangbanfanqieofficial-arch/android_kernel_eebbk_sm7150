#!/usr/bin/env python3
# Patch FocalTech touch driver to fix 90Hz touch failure.
# Pure ASCII only - avoids the encoding issues that broke the YAML earlier.
import sys, re

def main():
    p = sys.argv[1]
    s = open(p, encoding='utf-8', errors='replace').read()
    orig = s
    ok = 0

    # FIX 1: reset low pulse 1ms -> 20ms (FocalTech requires >=10ms)
    pat1 = re.compile(r'(gpio_direction_output\(fts_data->pdata->reset_gpio,\s*0\);\s*\n\s*)msleep\(1\);')
    if pat1.search(s):
        s = pat1.sub(r'\1msleep(20);  /* FTS_FIX reset low 20ms */', s, count=1)
        print("[OK] FIX1 reset low 1ms -> 20ms")
        ok += 1
    else:
        print("[WARN] FIX1 pattern not matched")

    # FIX 2+3: check wait_tp_to_valid return + retry; force POWER_MODE=ACTIVE
    m = re.search(r'( *)fts_reset_proc\(200\);\s*\n\s*fts_wait_tp_to_valid\(\);\s*\n\s*fts_ex_mode_recovery\(ts_data\);', s)
    if m:
        ind = m.group(1)
        lines = []
        lines.append(ind + "fts_reset_proc(200);")
        lines.append("")
        lines.append(ind + "/* FTS_FIX original code ignored fts_wait_tp_to_valid() return")
        lines.append(ind + " * value and enabled IRQ even on timeout, so the IC could be")
        lines.append(ind + " * not ready yet (log said TP Ready but no touch reports). */")
        lines.append(ind + "{")
        lines.append(ind + "    int retry, wret = -1;")
        lines.append(ind + "    for (retry = 0; retry < 3; retry++) {")
        lines.append(ind + "        wret = fts_wait_tp_to_valid();")
        lines.append(ind + "        if (wret == 0)")
        lines.append(ind + "            break;")
        lines.append(ind + '        pr_err("[FTS_FIX] resume tp not valid retry %d/3\\n", retry + 1);')
        lines.append(ind + "        fts_reset_proc(300);")
        lines.append(ind + "    }")
        lines.append(ind + "    if (wret != 0)")
        lines.append(ind + '        pr_err("[FTS_FIX] resume tp still not valid after retries\\n");')
        lines.append(ind + "}")
        lines.append("")
        lines.append(ind + "/* FTS_FIX suspend wrote POWER_MODE=SLEEP(0x03). If reset did not")
        lines.append(ind + " * clear it, IC stays asleep: I2C readable but no scan/report. */")
        lines.append(ind + "{")
        lines.append(ind + "    int pret = fts_write_reg(FTS_REG_POWER_MODE, 0x00);")
        lines.append(ind + "    if (pret < 0)")
        lines.append(ind + '        pr_err("[FTS_FIX] resume force ACTIVE failed %d\\n", pret);')
        lines.append(ind + "}")
        lines.append("")
        lines.append(ind + "fts_ex_mode_recovery(ts_data);")
        new = "\n".join(lines)
        s = s[:m.start()] + new + s[m.end():]
        print("[OK] FIX2+3 resume retry + force ACTIVE")
        ok += 1
    else:
        print("[WARN] FIX2 pattern not matched")

    if s == orig:
        print("!! nothing changed")
        return 1

    open(p, 'w', encoding='utf-8').write(s)
    print("patch written, %d fixes applied" % ok)
    return 0

if __name__ == '__main__':
    sys.exit(main())
