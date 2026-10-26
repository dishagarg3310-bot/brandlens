import pathlib

p = pathlib.Path("README.md")
t = p.read_text(encoding="utf-8")
start = t.find("- Before the 10:00 AM IST opening")
end = t.find("- Libraries:")
if start < 0 or end < 0:
    print("NOT FOUND")
else:
    new = ("- Initial project setup (skeleton, sample data, first rule module, basic screen) "
           "was done before the 10:00 AM opening on 26 Oct; all other features were built during Round 2.\n")
    p.write_text(t[:start] + new + t[end:], encoding="utf-8")
    print("patched")