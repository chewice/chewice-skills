# 芯片获取（兼容入口）

读取 `assays/array.md` 与 `sources/geo-supplement.md`。CEL/IDAT 由 `download_geo_supplement.py` 下载。平台元数据用 `download_geo_platform.py`：先尝试最小 GPL/platform-only 官方端点，失败后自动回退官方 family SOFT/MINiML；不下载 series matrix，不执行 RMA。
