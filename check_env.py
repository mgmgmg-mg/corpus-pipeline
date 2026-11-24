"""check_env.py —— 一次性验证数据工程环境

用法：python check_env.py
输出：8 个 [ OK ] 即环境就绪；有任何 [FAIL] 把那行贴给助教。
"""
import importlib
import sys

TESTS = {}


def test(name):
    def deco(fn):
        TESTS[name] = fn
        return fn
    return deco


@test("pandas")
def _(m):
    assert int(m.DataFrame({"a": [1, 2, 3]})["a"].sum()) == 6


@test("pyarrow")
def _(m):
    assert m.table({"x": [1, 2]}).num_rows == 2


@test("datasets")
def _(m):
    assert hasattr(m, "load_dataset")


@test("pdfplumber")
def _(m):
    assert hasattr(m, "open")


@test("bs4")
def _(m):
    assert m.BeautifulSoup("<p>hi</p>", "html.parser").p.text == "hi"


@test("requests")
def _(m):
    r = m.get("https://pypi.org/simple/", timeout=8)
    assert r.status_code in (200, 301, 302)


@test("datasketch")
def _(m):
    from datasketch import MinHash

    a, b = MinHash(), MinHash()
    for w in ["a", "b", "c"]:
        a.update(w.encode())
        b.update(w.encode())
    assert a.jaccard(b) > 0.99


@test("tqdm")
def _(m):
    list(m.tqdm(range(3), disable=True))


def main():
    ok = True
    print(f"python {sys.version.split()[0]}")
    print(f"exe    {sys.executable}")
    print("-" * 58)
    for name, fn in TESTS.items():
        try:
            m = importlib.import_module(name)
            fn(m)
            print(f"[ OK ] {name:<12} {getattr(m, '__version__', '-')}")
        except Exception as e:  # noqa: BLE001
            ok = False
            print(f"[FAIL] {name:<12} {type(e).__name__}: {e}")
    print("-" * 58)
    print("ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
