# ENA

- ENA `submitted` files 是作者提交对象；ENA archive-generated FASTQ 是归档系统从标准化对象生成的文件。二者必须使用不同 provenance/object class。
- submitted 文件若格式和下游兼容，应优先于 generated FASTQ；不兼容时记录选择证据和原因。
- 对每个 run 解析完整 URL、MD5、bytes、mate/read role。多文件数组必须保持索引对应，不能仅取第一项。
- FASTQ 中的 Phred 分布只能用于发现质量可能被简化，不能证明 submitted 或 generated provenance；provenance 来自官方文件分类和元数据。
- transport endpoint 可为 HTTPS/FTP，但与 provenance 分开记录。
