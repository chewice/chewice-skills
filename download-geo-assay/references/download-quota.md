# 峰值预算与滚动转换

预算以 GSM/文库为单位，同时计入来源对象、FASTQ 展开、`fasterq-dump` scratch、转换 scratch、processed 产物、下一单元预取和安全余量。SRA 转 FASTQ 时按 accession 约 8–10 倍 scratch 预留。

`audit_manifest.py` 比较项目上限、working/temporary 上限、可用空间和已知用户 quota，采用最严限制。若当前单元峰值不满足，不能启动下一单元。Mode B 逐单元下载、转换、审计和 release，不以“整批已下载”作为删除门。
