# ofd2img
## Prerequisite
1. Install [PyGobject](https://pygobject.readthedocs.io/en/latest/).
`https://pygobject.readthedocs.io/en/latest/getting_started.html#windows-getting-started`
2. Install [Jbig2Dec](https://github.com/ArtifexSoftware/jbig2dec)
不要用brew install (brew info jbig2dec)的那个，好像只支持转出为pbm，不支持png。
自己安装下。
```bash
git clone https://github.com/ArtifexSoftware/jbig2dec 
cd jbig2dec
./autogen && make && make install
jbig2dec -o image_80.png Doc_0/Res/image_80.jb2
```
## Usage
安装好对应的依赖，调用OFDFile.draw_document会生成发票的PNG图片。
```python
from core.document import OFDFile
doc = OFDFile('test.ofd')
doc.draw_document()  
# check test_Doc_0_Page_0.png under folder
```
# Need Help?
有任何问题请提Issue或者联系 **geniusnut@gmail.com**。

# Issues
发票签章位置Hardcode。
