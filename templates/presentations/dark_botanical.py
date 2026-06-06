# -*- coding: utf-8 -*-
"""
Dark Botanical 风格 HTML 演示文稿模板
=====================================

这是 html_generate 工具使用的预置模板之一。
提供优雅的深色主题，适合正式场合。

CSS 变量：
- --bg-primary: #0f0f0f (深色背景)
- --text-primary: #e8e4df (主文字)
- --text-secondary: #9a9590 (次要文字)
- --accent-warm: #d4a574 (暖色点缀)
- --accent-pink: #e8b4b8 (粉色点缀)
- --accent-gold: #c9b896 (金色点缀)

字体：
- 显示字体: Cormorant (Google Fonts)
- 正文字体: IBM Plex Sans (Google Fonts)
"""

DARK_BOTANICAL_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant:wght@400;500;600;700&family=IBM+Plex+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root {{
    --bg-primary: #0f0f0f;
    --text-primary: #e8e4df;
    --text-secondary: #9a9590;
    --accent-warm: #d4a574;
    --accent-pink: #e8b4b8;
    --accent-gold: #c9b896;
    --title-size: clamp(2rem, 5vw, 4rem);
    --h2-size: clamp(1.5rem, 3.5vw, 2.5rem);
    --body-size: clamp(0.9rem, 1.5vw, 1.2rem);
    --slide-padding: clamp(1.5rem, 5vw, 5rem);
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html {{ scroll-snap-type: y mandatory; scroll-behavior: smooth; }}
body {{ font-family: 'IBM Plex Sans', sans-serif; background: var(--bg-primary); color: var(--text-primary); overflow-x: hidden; }}
.slide {{ height: 100vh; height: 100dvh; overflow: hidden; scroll-snap-align: start; display: flex; flex-direction: column; position: relative; }}
.slide-content {{ flex: 1; display: flex; flex-direction: column; justify-content: center; padding: var(--slide-padding); max-height: 100%; }}
h1 {{ font-family: 'Cormorant', serif; font-size: var(--title-size); font-weight: 600; margin-bottom: 1rem; line-height: 1.2; }}
h2 {{ font-family: 'Cormorant', serif; font-size: var(--h2-size); font-weight: 500; margin-bottom: 1.5rem; color: var(--accent-warm); }}
p {{ font-size: var(--body-size); line-height: 1.7; color: var(--text-secondary); }}
.centered {{ text-align: center; align-items: center; }}
.bg-shape {{ position: absolute; border-radius: 50%; filter: blur(100px); opacity: 0.25; pointer-events: none; }}
.bg-warm {{ background: var(--accent-warm); }}
.bg-pink {{ background: var(--accent-pink); }}
.bg-gold {{ background: var(--accent-gold); }}
.data-card {{ background: rgba(212, 165, 116, 0.08); border: 1px solid rgba(212, 165, 116, 0.3); border-radius: 16px; padding: clamp(1.5rem, 3vw, 2.5rem); text-align: center; }}
.data-number {{ font-family: 'Cormorant', serif; font-size: clamp(2rem, 4vw, 3.5rem); font-weight: 600; color: var(--accent-warm); line-height: 1.2; }}
.data-label {{ font-size: clamp(0.85rem, 1.2vw, 1rem); color: var(--text-secondary); margin-top: 0.5rem; }}
.grid-3 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr)); gap: clamp(1rem, 2vw, 1.5rem); }}
.trend-item {{ display: flex; align-items: flex-start; gap: 1rem; padding: 1rem 0; border-bottom: 1px solid rgba(212, 165, 116, 0.15); }}
.trend-item:last-child {{ border-bottom: none; }}
.trend-icon {{ font-size: clamp(1.5rem, 2.5vw, 2rem); flex-shrink: 0; }}
.trend-content {{ flex: 1; }}
.trend-title {{ font-family: 'Cormorant', serif; font-size: clamp(1.1rem, 1.8vw, 1.4rem); color: var(--accent-warm); margin-bottom: 0.5rem; }}
.trend-desc {{ font-size: clamp(0.85rem, 1.2vw, 1rem); color: var(--text-secondary); line-height: 1.6; }}
@media (prefers-reduced-motion: reduce) {{ html {{ scroll-behavior: auto; }} }}
</style>
</head>
<body>
{slides}
</body>
</html>
'''

def generate_slide_title(title: str, subtitle: str = "") -> str:
    """生成标题页"""
    subtitle_html = f'<p style="font-size: clamp(1rem, 2vw, 1.3rem); color: var(--accent-warm); margin-top: 1rem;">{subtitle}</p>' if subtitle else ""
    return f'''
<section class="slide centered">
    <div class="bg-shape bg-warm" style="width: 50vmax; height: 50vmax; top: -15%; right: -10%;"></div>
    <div class="bg-shape bg-pink" style="width: 40vmax; height: 40vmax; bottom: -10%; left: -10%;"></div>
    <div class="slide-content" style="align-items: center;">
        <h1>{title}</h1>
        {subtitle_html}
    </div>
</section>
'''

def generate_slide_data(title: str, cards: list[dict]) -> str:
    """生成数据展示页"""
    cards_html = ""
    for card in cards:
        cards_html += f'''
        <div class="data-card">
            <div class="data-number">{card.get('value', '')}</div>
            <div class="data-label">{card.get('label', '')}</div>
        </div>
        '''
    return f'''
<section class="slide">
    <div class="bg-shape bg-pink" style="width: 35vmax; height: 35vmax; bottom: -10%; right: -5%;"></div>
    <div class="slide-content">
        <h2>{title}</h2>
        <div class="grid-3">
            {cards_html}
        </div>
    </div>
</section>
'''

def generate_slide_trends(title: str, trends: list[dict]) -> str:
    """生成趋势列表页"""
    trends_html = ""
    for trend in trends:
        trends_html += f'''
        <div class="trend-item">
            <span class="trend-icon">{trend.get('icon', '📌')}</span>
            <div class="trend-content">
                <div class="trend-title">{trend.get('title', '')}</div>
                <div class="trend-desc">{trend.get('description', '')}</div>
            </div>
        </div>
        '''
    return f'''
<section class="slide">
    <div class="bg-shape bg-gold" style="width: 30vmax; height: 30vmax; top: 10%; right: -5%;"></div>
    <div class="slide-content">
        <h2>{title}</h2>
        <div style="max-width: 800px;">
            {trends_html}
        </div>
    </div>
</section>
'''

def generate_slide_content(title: str, content: str) -> str:
    """生成内容文本页"""
    return f'''
<section class="slide">
    <div class="slide-content">
        <h2>{title}</h2>
        <p style="max-width: 700px; line-height: 1.8;">{content}</p>
    </div>
</section>
'''