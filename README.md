# Douyin Creator Assets Skill

抖音达人资产分析 Skill。用于采集达人公开作品的点赞、评论、收藏、分享数据，并生成达人资产库前两项：

1. 账号公开互动基础盘
2. 账号内容资产盘
   - 2A 标题/话题/商品信号粗筛
   - 2B 媒体内容细看
   - 2C 优质内容到儿童营养品议题的转接预判

## 安装

把整个 `douyin-creator-assets` 文件夹复制到你的 Skill 目录，或在支持本地 Skill 的 Agent 中引用本文件夹。

目录结构应保持如下：

```text
douyin-creator-assets/
  SKILL.md
  README.md
  agents/
  references/
  scripts/
```

## 输入

至少提供以下任一项：

- 抖音账号分享文案
- 抖音账号主页链接
- 抖音视频分享文案或视频链接
- `aweme_id`
- 已整理好的达人作品 CSV / JSON

## 快速开始

在任意项目工作目录中运行：

```bash
python3 path/to/douyin-creator-assets/scripts/collect_creator_assets.py '抖音账号分享信息或主页链接'
```

指定普通主页作品样本数：

```bash
python3 path/to/douyin-creator-assets/scripts/collect_creator_assets.py 'https://www.douyin.com/user/xxx' --count 10
```

默认输出到当前工作目录：

```text
outputs/douyin_creator_assets/<timestamp>/
```

生成 2A 内容资产粗筛：

```bash
python3 path/to/douyin-creator-assets/scripts/analyze_content_assets.py outputs/douyin_creator_assets/<timestamp>
```

如果第一项基础盘 CSV/JSON 已存在，但缺少第一项 Markdown 文档，可补渲染：

```bash
python3 path/to/douyin-creator-assets/scripts/render_basic_profile.py outputs/douyin_creator_assets/<timestamp>
```

补渲染会输出：

```text
01_公开互动基础盘.md
01_挂车作品公开互动基础盘.md（有挂车短视频样本时）
```

生成 2B 媒体细看候选清单：

```bash
python3 path/to/douyin-creator-assets/scripts/select_video_samples.py outputs/douyin_creator_assets/<timestamp>
```

该脚本会输出：

```text
02B_媒体细看抽样清单数据.csv
02B_媒体细看抽样清单.md
```

下载 2B 候选媒体：

```bash
python3 path/to/douyin-creator-assets/scripts/download_sample_videos.py outputs/douyin_creator_assets/<timestamp>
```

下载后会输出：

```text
02B_候选媒体下载结果.csv
2b_<作品ID>.mp4（视频作品）
2b_<作品ID>_images/（图片/图文作品）
2b_<作品ID>_images.json（图片/图文作品）
2b_<作品ID>.url.txt
2b_<作品ID>.raw.json
```

视频作品抽帧生成 grid 图：

```bash
python3 path/to/douyin-creator-assets/scripts/extract_video_frames.py outputs/douyin_creator_assets/<timestamp>
```

抽帧后会输出：

```text
02B_视频抽帧结果.csv
2b_<作品ID>_grid.jpg
```

图片/图文作品不需要抽帧，后续 handoff 会直接带上图片文件路径。

生成媒体理解交接包：

```bash
python3 path/to/douyin-creator-assets/scripts/build_video_understanding_handoff.py outputs/douyin_creator_assets/<timestamp>
```

交接包不绑定任何模型或厂商。它会把 mp4、抽帧图、图片文件、可选字幕路径、互动数据和 2B 输出字段打包，交给 WorkBuddy 或其他能看视频/图片的 Agent 逐条回填 JSON。

交接包会输出：

```text
02B_媒体理解交接包.jsonl
02B_媒体理解交接包.md
```

外部 Agent 回填后，建议保存为：

```text
video_understanding_results.jsonl
```

再渲染 2B 媒体内容细看：

```bash
python3 path/to/douyin-creator-assets/scripts/render_video_deep_dive.py outputs/douyin_creator_assets/<timestamp>
```

生成 2C 营养品转接预判：

```bash
python3 path/to/douyin-creator-assets/scripts/render_nutrition_transfer.py outputs/douyin_creator_assets/<timestamp>
```

## 产物

正式产物优先看中文文件名；脚本会同时保留英文兼容副本，供旧流程或其他 Agent 读取。

第一项基础盘：

- `01_主页普通作品明细.csv`
- `01_挂车作品明细.csv`
- `01_公开互动基础盘数据.csv`
- `01_挂车作品公开互动基础盘数据.csv`
- `01_公开互动基础盘.md`
- `01_挂车作品公开互动基础盘.md`
- `raw.json`

第二项内容资产盘：

- `02A_内容资产粗筛明细.csv`
- `02A_内容资产粗筛.md`
- `02A_挂车作品内容资产粗筛明细.csv`（有挂车短视频样本时）
- `02A_挂车作品内容资产粗筛.md`（有挂车短视频样本时）
- `02B_媒体细看抽样清单数据.csv`
- `02B_媒体细看抽样清单.md`
- `02B_候选媒体下载结果.csv`
- `02B_视频抽帧结果.csv`
- `02B_媒体理解交接包.jsonl`
- `02B_媒体理解交接包.md`
- `video_understanding_results.jsonl`（外部 Agent 回填）
- `02B_媒体内容细看明细.csv`
- `02B_媒体内容细看.md`
- `02C_营养品议题转接预判明细.csv`
- `02C_营养品议题转接预判.md`

## 执行边界

第一项只判断公开互动基础盘，不判断达人是否适合合作、转化率、ROI 或具体产品适配。

第二项只判断账号内容资产盘。2C 只判断已验证的优质内容结构能否自然转成儿童营养品议题，不写某个具体产品怎么接，不判断转化率或合作价值。

## 关键规则

- 播放量不进入表格、汇总和判断。
- 置顶视频不进入普通主页基础盘。
- 挂车短视频单独分析，不混入主页普通短视频。
- 点赞、评论、收藏、分享必须分别看，不用总互动替代四项判断。
- 2B 抽样必须覆盖四项互动的高位、低位和强品类连接低互动样本。
- 2B 媒体理解不绑定任何单一供应商；Skill 只负责准备交接包和渲染结果，具体视频/图片理解可由 WorkBuddy 或其他 Agent 完成。
- 2B 样本可能是视频，也可能是图片/图文；下载脚本必须按媒体类型处理，不能默认全是 mp4。
- 2C 固定链条：

```text
已验证优质内容结构
-> 起量机制
-> 对应的家长问题
-> 营养品可转接议题
-> 必须保留的表达方式
-> 风险
-> 评论验证点
```

## 依赖

脚本使用 Python 3 标准库。采集主页作品时需要 Playwright：

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

抽帧需要本机安装 `ffmpeg` 和 `ffprobe`。

如果运行环境无法访问抖音公开网页或接口，采集可能失败；这种情况下可以输入已整理好的 CSV / JSON 继续做分析。
