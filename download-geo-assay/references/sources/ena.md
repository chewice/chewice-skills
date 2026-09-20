# ENA

- ENA `submitted` files 是作者提交对象；ENA archive-generated FASTQ 是归档系统从标准化对象生成的文件。二者必须使用不同 provenance/object class。
- submitted 文件若格式和下游兼容，应优先于 generated FASTQ；不兼容时记录选择证据和原因。
- 对每个 run 解析完整 URL、MD5、bytes、mate/read role。多文件数组必须保持索引对应，不能仅取第一项。
- paired 文件不能仅凭 URL 数组顺序指定 R1/R2；角色不明时保留待核实状态。当前下载器每个 run/role 只有一个目标文件，同一 run 的重复角色（如多 lane 的两组 R1/R2）须在下载前阻断，不覆盖或擅自合并。
- 每个候选先核对最终产物、角色及逐文件 bytes/MD5，再参与排序。要求 SRA 产物时不选择 FASTQ；submitted 候选不合格时可选择其他合格候选，并在 `selection_reason` 留下原因。明确指定 ENA 时不得自动改用 NCBI。
- FASTQ 中的 Phred 分布只能用于发现质量可能被简化，不能证明 submitted 或 generated provenance；provenance 来自官方文件分类和元数据。
- transport endpoint 可为 HTTPS/FTP，但与 provenance 分开记录。
