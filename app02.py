import streamlit as st
import pandas as pd
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.transform import factor_cmap
from bokeh.palettes import Category20

# 1. 页面基本设置
st.set_page_config(page_title="Power Bank Dashboard", layout="wide")
st.title("🔋 充电宝市场价格与容量分析面板")

# 2. 数据读取与清洗
@st.cache_data(ttl=600)
def load_data():
    sheet_url = "https://docs.google.com/spreadsheets/d/1fkMRXkdKVdYFN3d_Y7bhFtA1BGIUlA3xAG86UvvhT1w/export?format=csv&gid=0"
    df = pd.read_csv(sheet_url)
    
    # 清洗价格列：提取数字
    if 'Price' in df.columns:
        df['Price'] = pd.to_numeric(df['Price'].astype(str).str.replace('[\$,]', '', regex=True), errors='coerce')
    
    # 【核心修复】先删掉没有价格或没有容量的数据（没有 X 和 Y 坐标无法画图）
    df = df.dropna(subset=['Price', 'Capacity/mAh'])
    
    # 然后再将其他缺失的文本字段（如接口、尺寸等）填充为 'N/A'，确保悬停框显示整洁
    df = df.fillna('N/A')
    
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"数据读取失败: {e}")
    st.stop()

# 3. 侧边栏：刷新按钮与筛选器
st.sidebar.header("⚙️ 控制面板")
if st.sidebar.button("🔄 刷新数据"):
    st.cache_data.clear()
    st.rerun()

if 'Brand' in df.columns:
    brands = df['Brand'].unique().tolist()
    # 过滤掉 'N/A' 等无效品牌
    brands = [b for b in brands if b != 'N/A']
    selected_brands = st.sidebar.multiselect("🏷️ 筛选品牌", options=brands, default=brands)
    filtered_df = df[df['Brand'].isin(selected_brands)]
else:
    st.stop()

# 4. 数据预处理 (为 Bokeh 绘图做准备)
temp_df = filtered_df.copy()

# 【优化点】提取容量里的纯数字并排序，确保 X 轴的容量是从小到大排列的
temp_df['cap_num'] = pd.to_numeric(temp_df['Capacity/mAh'].astype(str).str.extract(r'(\d+)')[0], errors='coerce').fillna(0)
temp_df = temp_df.sort_values('cap_num')

# 提取排好序的唯一容量值作为 X 轴标签
x_range = temp_df['Capacity/mAh'].astype(str).unique().tolist()
temp_df['Capacity/mAh_str'] = temp_df['Capacity/mAh'].astype(str)

# 将 DataFrame 转换为 Bokeh 需要的数据源格式
source = ColumnDataSource(temp_df)

# 设置品牌颜色映射
unique_brands = temp_df['Brand'].unique().tolist()
palette = Category20[20] if len(Category20) > 0 else []
# 确保颜色足够分配
while len(palette) < len(unique_brands):
    palette += Category20[20]
color_map = factor_cmap('Brand', palette=palette[:max(1, len(unique_brands))], factors=unique_brands)

# 5. 绘制 Bokeh 散点图
p = figure(x_range=x_range, height=700, sizing_mode="stretch_width", 
           title="鼠标悬停在圆点上查看产品大图与详情",
           toolbar_location="right", tools="pan,wheel_zoom,box_zoom,reset")

# 绘制散点
scatter = p.circle(x='Capacity/mAh_str', y='Price', size=16, source=source, 
                   color=color_map, legend_field='Brand', fill_alpha=0.8, 
                   line_color="white", line_width=1.5)

# 优化图例和坐标轴显示
p.legend.location = "top_left"
p.legend.click_policy = "hide"  # 允许用户点击图例隐藏某个品牌
p.legend.title = "Brand (Click to hide)"
p.xaxis.axis_label = "电池容量 (Capacity / mAh)"
p.yaxis.axis_label = "价格 (Price / USD)"
p.xaxis.major_label_text_font_size = "10pt"
p.yaxis.major_label_text_font_size = "10pt"

# 6. 绝美的 HTML 悬停框 (HoverTool)
# 注意：在 Bokeh 中，调用字段值使用 @{列名}
hover = HoverTool(renderers=[scatter])
hover.tooltips = """
<div style="width: 250px; background: white; padding: 10px; border-radius: 10px; box-shadow: 0px 4px 10px rgba(0,0,0,0.15);">
    <div style="text-align:center;">
        <img src="@{URL of Image}" style="width: 150px; border-radius: 8px; margin-bottom: 10px;">
        <div style="font-weight: bold; font-size: 14px; color: #333; margin-bottom: 5px;">@{Brand} - @{Model Number}</div>
    </div>
    <hr style="margin: 8px 0; border: 0; border-top: 1px solid #eaeaea;">
    <table style="width: 100%; font-size: 12px; color: #444; line-height: 1.6;">
        <tr><td style="padding: 2px 0;"><b>💰 Price:</b></td><td style="text-align: right; color:#d9534f; font-weight:bold;">$@{Price}</td></tr>
        <tr><td style="padding: 2px 0;"><b>🔋 Capacity:</b></td><td style="text-align: right;">@{Capacity/mAh}</td></tr>
        <tr><td style="padding: 2px 0;"><b>🔌 Ports:</b></td><td style="text-align: right;">@{Connect Type}</td></tr>
        <tr><td style="padding: 2px 0;"><b>⚡ Fast Charge:</b></td><td style="text-align: right;">@{Fast charging}</td></tr>
        <tr><td style="padding: 2px 0;"><b>📶 Wireless:</b></td><td style="text-align: right;">@{Wireless}</td></tr>
        <tr><td style="padding: 2px 0;"><b>⭐ Rating:</b></td><td style="text-align: right;">@{Rating} (@{Number of Reviews})</td></tr>
        <tr><td style="padding: 2px 0;"><b>📦 Size:</b></td><td style="text-align: right;">@{Size}</td></tr>
        <tr><td style="padding: 2px 0;"><b>⚖️ Weight:</b></td><td style="text-align: right;">@{Weight}</td></tr>
        <tr><td style="padding: 2px 0;"><b>🛒 Sold by:</b></td><td style="text-align: right;">@{Sold by}</td></tr>
    </table>
</div>
"""
p.add_tools(hover)

# 7. 在 Streamlit 中渲染
st.bokeh_chart(p, use_container_width=True)

# 底部数据预览表
with st.expander("📊 查看底层原始数据"):
    st.dataframe(filtered_df)
