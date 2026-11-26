"""Geniality: automatic App Store signing with the distribution certificate already installed."""
import os, re, sys

PATH = "ios/App/App.xcodeproj/project.pbxproj"
TEAM = "3GU37GL28P"
BUNDLE = "com.toplinesupport.geniality"
PROFILE = os.environ.get("PROFILE_NAME", "Geniality App Store")

s = open(PATH).read()

def block_at(text, i):
    start = text.rfind("{", 0, i)
    depth = 0
    for j in range(start, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return start, j + 1
    return start, len(text)

patched = 0
out = s
for m in reversed(list(re.finditer(r"isa = XCBuildConfiguration;", s))):
    a, b = block_at(s, m.start())
    block = s[a:b]
    if "INFOPLIST_FILE = App/Info.plist" not in block:
        continue
    block = re.sub(r"\n\s*(CODE_SIGN_STYLE|CODE_SIGN_IDENTITY|PROVISIONING_PROFILE_SPECIFIER|DEVELOPMENT_TEAM|PRODUCT_BUNDLE_IDENTIFIER) = [^;]*;", "", block)
    add = (
        "\n\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = %s;"
        "\n\t\t\t\tCODE_SIGN_STYLE = Manual;"
        '\n\t\t\t\tCODE_SIGN_IDENTITY = "Apple Distribution";'
        "\n\t\t\t\tPROVISIONING_PROFILE_SPECIFIER = %s;"
        "\n\t\t\t\tDEVELOPMENT_TEAM = %s;" % (BUNDLE, PROFILE, TEAM)
    )
    block = block.replace("INFOPLIST_FILE = App/Info.plist;", "INFOPLIST_FILE = App/Info.plist;" + add, 1)
    out = out[:a] + block + out[b:]
    patched += 1

open(PATH, "w").write(out)

pods = "ios/App/Pods/Pods.xcodeproj/project.pbxproj"
try:
    t = open(pods).read()
    t = re.sub(r"\n\s*(CODE_SIGN_STYLE|CODE_SIGN_IDENTITY|PROVISIONING_PROFILE_SPECIFIER|DEVELOPMENT_TEAM) = [^;]*;", "", t)
    t = t.replace(
        "PRODUCT_NAME = ",
        'CODE_SIGN_STYLE = Manual; CODE_SIGN_IDENTITY = "Apple Distribution"; DEVELOPMENT_TEAM = %s; PRODUCT_NAME = ' % TEAM,
    )
    open(pods, "w").write(t)
    print("signed the Pods frameworks")
except FileNotFoundError:
    print("no Pods project yet")
print("patched %d App target configurations" % patched)
if patched == 0:
    sys.exit("no App target configuration found")
