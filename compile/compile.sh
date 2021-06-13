#!/usr/bin/env bash
cp -R -u ../pysimpledlna .
cp -R -u ../../prompt_toolkit_ext/prompt_toolkit_ext .
export output_name=$(date "+%Y%m%d%H%M%S")_win32
export output_dir=../../$output_name
echo $output_dir
python -m nuitka --mingw64 --show-progress --standalone --output-dir=$output_dir --nofollow-import-to=pygments --nofollow-import-to=PIL --nofollow-import-to=pytest --nofollow-import-to=OpenSSL --nofollow-import-to=service_identity --nofollow-import-to=prompt_toolkit --nofollow-import-to=Bottle --nofollow-import-to=cryptography ./pysimpledlna.py
mkdir -p $output_dir/pysimpledlna.dist/pysimpledlna/templates
cp -R ./pysimpledlna/templates $output_dir/pysimpledlna.dist/pysimpledlna
cp ./pysimpledlna/bottle.*.pyd $output_dir/pysimpledlna.dist/
cp ./pysimpledlna/prompt_toolkit.*.pyd $output_dir/pysimpledlna.dist/
rm -rf $output_dir/pysimpledlna.build