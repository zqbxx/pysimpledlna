#!/usr/bin/env bash
cp -R -u ../pysimpledlna .
cp -R -u ../../prompt_toolkit_ext/prompt_toolkit_ext .
export output_name=$(date "+%Y%m%d%H%M%S")_win32
export output_dir=../../$output_name
echo $output_dir
python ./compile.py $output_dir
mkdir -p $output_dir/pysimpledlna.dist/pysimpledlna/templates
cp -R ./pysimpledlna/templates $output_dir/pysimpledlna.dist/pysimpledlna
cp $output_dir/pysimpledlna.dist/pysimpledlna.exe $output_dir/pysimpledlna.dist/pysd.exe
rm -rf $output_dir/pysimpledlna.build