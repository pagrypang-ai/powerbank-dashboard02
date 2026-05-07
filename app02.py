import streamlit as st
import pandas as pd
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, Range1d
import numpy as np

# 页面配置
st.set_page_config(page_title="产品动态对比看板", layout="wide")

# Google Sheets CSV 导出链接
SHEET_URL = "https://docs.google.com/spreadsheets/d/1fkMRXkdKVdYFN3d_Y7bhFtA1BGIUlA3xAG86UvvhT1w/export?format=csv&gid=0"

@st.cache_data
def load_data(url):
    df = pd.read_csv(url)
    
    # 1. 数据预处理 - Price 转换为浮点数
    # 去除可能存在的货币符号和逗号
    if df['Price'].dtype == 'object':
        df['Price'] = df['Price'].replace(r'[$,]', '', regex=True).astype(float)
    
    # 2. 数据预处理 - Capacity/mAh 转换为离散排序字符串
    # 确保 X 轴按数值大小排列而非字母排列
    df['Capacity_Val'] = pd.to_numeric(df['Capacity/mAh'], errors='coerce').fillna(0)
    df = df.sort_values(by='Capacity_Val')
    df['Capacity/mAh'] = df['Capacity/mAh'].astype(str)
    
    return df

# --- 侧边栏交互 ---
st.sidebar.header("控制面板")

# 刷新按钮
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# 加载数据
try:
    df_raw = load_data(SHEET_URL)
except Exception as e:
    st.error(f"数据加载失败，请检查 Google Sheets 链接是否已发布为 CSV。错误: {e}")
    st.stop()

# 品牌筛选
all_brands = df_raw['Brand'].unique().tolist()
selected_brands = st.sidebar.multiselect("选择品牌", options=all_brands, default=all_brands)

# 过滤数据
df_filtered = df_raw[df_raw['Brand'].isin(selected_brands)].copy()

# --- 主界面 ---
st.title("🔋 产品对比看板 (Capacity vs Price)")
st.markdown("基于实时 Google Sheets 数据构建。悬停在图片上查看详细参数。")

if df_filtered.empty:
    st.warning("请至少选择一个品牌。")
else:
    # 准备 Bokeh 数据源
    source = ColumnDataSource(df_filtered)

    # 获取 X 轴所有可能的分类（用于排序）
    x_range = df_raw['Capacity/mAh'].unique().tolist()

    # --- 修改 3：根据 Price 数据范围设置 Y 轴留白，防止图片被截断 ---
    price_min = df_filtered['Price'].min()
    price_max = df_filtered['Price'].max()
    price_padding = (price_max - price_min) * 0.2 if price_max != price_min else 10
    y_range = Range1d(
        start=max(0, price_min - price_padding),
        end=price_max + price_padding
    )

    # 创建 Bokeh 图表
    p = figure(
        x_range=x_range,
        y_range=y_range,           # 修改 3：应用 Y 轴范围
        height=600,
        title="容量 vs 价格 散点图 (图片标记)",
        x_axis_label="Capacity (mAh)",
        y_axis_label="Price ($)",
        tools="pan,wheel_zoom,box_zoom,reset,save",
        active_scroll="wheel_zoom",
        sizing_mode="stretch_width"
    )

    # 绘制图片散点
    # --- 修改 2：h_units 从 "screen" 改为 "data"，避免分类轴兼容性报错 ---
    img_glyphs = p.image_url(
        url="URL of Image", 
        x="Capacity/mAh", 
        y="Price", 
        source=source,
        anchor="center",
        w=0.4,
        h=price_padding,           # 修改 2：高度与数据坐标系匹配
        w_units="data",
        h_units="data"             # 修改 2：统一使用 data 单位
    )

    # --- 修改 1：新增透明散点层，作为 HoverTool 的触发器 ---
    # image_url glyph 不能可靠触发 HoverTool，
    # 在相同坐标叠加透明 circle，将 Hover 绑定到它上面
    invisible_scatter = p.circle(
        x="Capacity/mAh",
        y="Price",
        source=source,
        size=40,               # 触发区域大小（像素），覆盖图片范围
        fill_alpha=0,          # 完全透明，用户不可见
        line_alpha=0           # 边框也透明
    )

    # 构建立体 HTML 悬停提示
    tooltips = f"""
    <div style="padding: 10px; background-color: #f5f5f5; border: 1px solid #ddd; border-radius: 5px; width: 300px; font-family: sans-serif;">
        <div style="text-align: center; margin-bottom: 8px;">
            <img src="@{{URL of Image}}" style="width: 100px; border-radius: 4px;">
        </div>
        <div style="font-size: 14px; font-weight: bold; color: #1f77b4; margin-bottom: 5px;">@{{Brand}} - @{{Model Number}}</div>
        <hr>
        <div style="font-size: 12px; line-height: 1.5;">
            <b>💰 Price:</b> $@{{Price}} (Was: $@{{Was Price}})<br>
            <b>⚡ Capacity:</b> @{{Capacity/mAh}} mAh<br>
            <b>⭐ Rating:</b> @{{Rating}} (@{{Number of Reviews}} reviews)<br>
            <b>📦 Sold by:</b> @{{Sold by}}<br>
            <b>🚚 Pickup:</b> @{{Pickup or not}}<br>
            <b>📐 Size/Weight:</b> @{{Size}} / @{{Weight}}<br>
            <b>🔌 Connect:</b> @{{Connect Type}} (Wireless: @{{Wireless}})<br>
            <b>🚀 Fast Charge:</b> @{{Fast charging}} | <b>🔋 Indicator:</b> @{{Battery Indicator}}<br>
            <b>🛡️ Warranty:</b> @{{Warranty}}<br>
            <b>📝 Note:</b> @{{Note}}<br>
        </div>
        <div style="margin-top: 10px; text-align: center;">
            <a href="@{{Link}}" target="_blank" style="background-color: #4CAF50; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 11px;">View Product Link</a>
        </div>
    </div>
    """

    # --- 修改 4：HoverTool 绑定到透明散点层，而非 image_url ---
    hover = HoverTool(renderers=[invisible_scatter], tooltips=tooltips)
    p.add_tools(hover)

    # 美化图表
    p.title.text_font_size = '16pt'
    p.xaxis.major_label_orientation = 0.785 # 45度倾斜
    p.background_fill_color = "#fafafa"

    # 在 Streamlit 中展示
    st.bokeh_chart(p, use_container_width=True)

    # 展示原始数据表（可选）
    with st.expander("查看筛选后的原始数据"):
        st.dataframe(df_filtered.drop(columns=['Capacity_Val']), use_container_width=True)
