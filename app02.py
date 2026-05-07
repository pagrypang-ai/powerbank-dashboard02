import streamlit as st
import pandas as pd
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.transform import factor_cmap
from bokeh.palettes import Category20
import re

st.set_page_config(page_title="Power Bank Dashboard", layout="wide")
st.title("🔋 充电宝对比可视化看板")

@st.cache_data(ttl=600)
def load_data():
    sheet_url = "https://docs.google.com/spreadsheets/d/1fkMRXkdKVdYFN3d_Y7bhFtA1BGIUlA3xAG86UvvhT1w/export?format=csv&gid=0"
    df = pd.read_csv(sheet_url)
    
    # 【强制保护】即便你在原始数据排除了空格，这里加上 strip() 也是为了防止 CSV 导出时产生新空格
    df.columns = df.columns.str.strip()
    
    # 转换价格为数字
    if 'Price' in df.columns:
        df['Price'] = pd.to_numeric(df['Price'].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
    
    # 【检查点】如果这里删除了所有行，说明 'Price' 或 'Capacity/mAh' 匹配失败
    df = df.dropna(subset=['Price', 'Capacity/mAh'])
    df = df.fillna('')
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"数据读取失败: {e}")
    st.stop()

# --- 侧边栏 ---
st.sidebar.header("⚙️ 选项")
if st.sidebar.button("🔄 刷新数据"):
    st.cache_data.clear()
    st.rerun()

# 品牌筛选逻辑
if 'Brand' in df.columns:
    all_brands = sorted(df['Brand'].unique().tolist())
    selected_brands = st.sidebar.multiselect("筛选品牌", options=all_brands, default=all_brands)
    filtered_df = df[df['Brand'].isin(selected_brands)].copy()
else:
    st.error(f"❌ 错误：在表格中没找到 'Brand' 列。当前列名有：{df.columns.tolist()}")
    st.stop()

# 【关键排查】如果原始数据不显示，通常是 filtered_df 变成了空
if filtered_df.empty:
    st.warning("⚠️ 警告：当前筛选后的数据为空。请检查过滤器或原始表格中的价格/容量是否填写。")
    # 即便为空，我们也继续往下走，看看底部的表格显示什么
else:
    # ==========================================
    # 核心：严格匹配 x_range
    # ==========================================
    # 1. 强制生成绘图专用的字符串列
    filtered_df['x_axis_str'] = filtered_df['Capacity/mAh'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)

    # 2. 逻辑排序逻辑
    def extract_num(s):
        nums = re.findall(r'\d+', str(s))
        return int(nums[0]) if nums else 0
    filtered_df['cap_order'] = filtered_df['x_axis_str'].apply(extract_num)
    filtered_df = filtered_df.sort_values('cap_order')

    # 3. 严格提取 x_range 刻度
    unique_x_labels = filtered_df['x_axis_str'].unique().tolist()
    source = ColumnDataSource(filtered_df)

    # 颜色与绘图
    brands_list = filtered_df['Brand'].unique().tolist()
    color_palette = (Category20[20] * 2)[:len(brands_list)]
    color_map = factor_cmap('Brand', palette=color_palette, factors=brands_list)

    p = figure(x_range=unique_x_labels, height=600, sizing_mode="stretch_width", 
               title="鼠标悬停查看详情", toolbar_location="right")

    scatter = p.circle(x='x_axis_str', y='Price', size=18, source=source,
                       color=color_map, legend_field='Brand', fill_alpha=0.7)

    # 悬停提示
    hover = HoverTool(renderers=[scatter])
    hover.tooltips = """
    <div style="width: 260px; background: white; padding: 10px; border-radius: 8px; border: 1px solid #ddd;">
        <img src="@{URL of Image}" style="width: 100%; max-height: 150px; object-fit: contain; margin-bottom: 5px;">
        <div style="font-weight: bold; color: #1f77b4;">@{Brand}</div>
        <div>Price: <span style="color:red;">$@{Price}</span></div>
        <div>Capacity: @{Capacity/mAh}</div>
        <div>Connect: @{Connect Type}</div>
    </div>
    """
    p.add_tools(hover)
    
    st.bokeh_chart(p, use_container_width=True)

# --- 无论是否有图表，始终显示底部的原始数据预览 ---
st.markdown("---")
st.subheader("📊 原始数据预览")
if not df.empty:
    st.write(f"总共读取到 {len(df)} 行有效数据（已剔除价格或容量为空的行）")
    st.dataframe(df)
else:
    st.error("无法显示预览：读取到的有效数据行为 0。请检查 Google Sheets 中 'Price' 和 'Capacity/mAh' 列是否填写正确。")
