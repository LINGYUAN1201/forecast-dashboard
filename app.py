import pickle
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, dash_table
from encryption_utils import FileEncryptor  # 请确保该文件存在，并包含加密/解密实现

# 文件路径设置
original_file = 'data/forecast_results.pkl'                # 原始预测结果（明文）
encrypted_file = 'data/encrypted_forecast_results.pkl'        # 加密后的文件
decrypted_file = 'data/decrypted_forecast_results.pkl'        # 解密后临时文件

# 解密数据函数：使用指定密码解密加密文件，保存为临时明文文件
def decrypt_data():
    encryptor = FileEncryptor("your_password_here")  # 修改为您的加密密码
    encryptor.decrypt_file(encrypted_file, decrypted_file)

# 尝试加载预测结果数据
try:
    decrypt_data()  # 先解密文件
    with open(decrypted_file, 'rb') as f:
        forecast_results = pickle.load(f)
except (FileNotFoundError, pickle.UnpicklingError) as e:
    forecast_results = {}
    print("预测结果文件未找到或解密失败，请确认加密密码正确，或先运行预测脚本。错误信息：", e)

# 从 forecast_results 的 key 中获取城市、变量和模型列表
cities = sorted(list({key[0] for key in forecast_results.keys()}))
forecast_vars = sorted(list({key[1] for key in forecast_results.keys()}))
models = sorted(list({key[2] for key in forecast_results.keys()}))

# 创建 Dash 应用
app = Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])
server = app.server  # 供 Gunicorn 使用


# 定义颜色方案
COLORS = {
    "background": "#f9f9f9",
    "text": "#2c3e50",
    "primary": "#3498db",
    "secondary": "#e74c3c",
    "accent": "#2ecc71"
}

# 定义应用布局
app.layout = html.Div(style={'backgroundColor': COLORS['background'], 'fontFamily': 'Arial, sans-serif'}, children=[
    # 标题部分
    html.Div([
        html.H1("Forecast Dashboard", style={'textAlign': 'center', 'color': COLORS['text'], 'padding': '20px'}),
        html.P("Analyze and compare forecasts across cities, variables, and models.", 
               style={'textAlign': 'center', 'color': '#7f8c8d', 'fontSize': '16px'})
    ]),

    # 控制面板
    html.Div([
        html.Div([
            html.Label("Select City:", style={'color': COLORS['text']}),
            dcc.Dropdown(
                id='city-dropdown',
                options=[{'label': c, 'value': c} for c in cities],
                value=cities[0] if cities else None,
                clearable=False,
                placeholder="Choose a city..."
            )
        ], style={'width': '30%', 'margin': 'auto', 'padding': '10px'}),

        html.Div([
            html.Label("Select Forecast Variable:", style={'color': COLORS['text']}),
            dcc.Dropdown(
                id='variable-dropdown',
                options=[{'label': var, 'value': var} for var in forecast_vars],
                value=forecast_vars[0] if forecast_vars else None,
                clearable=False,
                placeholder="Choose a variable..."
            )
        ], style={'width': '30%', 'margin': 'auto', 'padding': '10px'}),

        html.Div([
            html.Label("Select Models (multi-select):", style={'color': COLORS['text']}),
            dcc.Dropdown(
                id='model-dropdown',
                options=[{'label': model.replace('_', ' ').capitalize(), 'value': model} for model in models],
                value=models,  # 默认选择所有模型
                multi=True,
                clearable=False,
                placeholder="Choose one or more models..."
            )
        ], style={'width': '30%', 'margin': 'auto', 'padding': '10px'}),
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'margin': '0 auto', 'maxWidth': '90%'}),

    # 图表区域
    html.Div([
        dcc.Loading(
            id="loading-graph",
            type="circle",
            children=dcc.Graph(id='forecast-graph', style={'height': '500px', 'margin': 'auto'}),
        )
    ], style={'padding': '20px', 'backgroundColor': '#ffffff', 'borderRadius': '8px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'}),

    # 错误指标表格
    html.Div([
        html.H2("Error Metrics by Model", style={'textAlign': 'center', 'color': COLORS['text'], 'paddingTop': '20px'}),
        dash_table.DataTable(
            id='error-metrics-table',
            columns=[
                {"name": "Model", "id": "Model"},
                {"name": "MAE", "id": "MAE"},
                {"name": "MSE", "id": "MSE"},
                {"name": "RMSE", "id": "RMSE"}
            ],
            style_table={'overflowX': 'auto', 'width': '80%', 'margin': 'auto', 'borderRadius': '8px'},
            style_cell={'textAlign': 'center', 'padding': '10px', 'fontSize': '14px', 'color': COLORS['text']},
            style_header={'fontWeight': 'bold', 'backgroundColor': COLORS['primary'], 'color': 'white'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f9f9f9'}]
        )
    ], style={'padding': '20px', 'backgroundColor': '#ffffff', 'borderRadius': '8px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'})
])

# 回调函数：更新图表和误差指标表格
@app.callback(
    [Output('forecast-graph', 'figure'),
     Output('error-metrics-table', 'data')],
    [Input('city-dropdown', 'value'),
     Input('variable-dropdown', 'value'),
     Input('model-dropdown', 'value')]
)
def update_dashboard(selected_city, selected_variable, selected_models):
    if not selected_models:
        return go.Figure(), []
    
    table_data = []
    fig = go.Figure()
    actual_plotted = False
    colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
        '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5'
    ]
    
    global_y_min, global_y_max = float('inf'), float('-inf')
    
    # 遍历所有模型的数据，计算全局 Y 轴范围
    for idx, model in enumerate(selected_models):
        key = (selected_city, selected_variable, model)
        if key not in forecast_results:
            continue
        data = forecast_results[key]
        hist_df = data['historical_df']
        future_df = data['forecast_future_df']
        
        global_y_min = min(global_y_min, hist_df['actual'].min(), 
                           hist_df['test_forecast'].min() if 'test_forecast' in hist_df.columns else float('inf'))
        global_y_max = max(global_y_max, hist_df['actual'].max(), 
                           hist_df['test_forecast'].max() if 'test_forecast' in hist_df.columns else float('-inf'))
        
        if not future_df.empty and 'final_forecast' in future_df.columns:
            global_y_min = min(global_y_min, future_df['final_forecast'].min())
            global_y_max = max(global_y_max, future_df['final_forecast'].max())
    
    train_end_date, test_start_date, test_end_date = None, None, None
    for idx, model in enumerate(selected_models):
        key = (selected_city, selected_variable, model)
        if key not in forecast_results:
            continue
        data = forecast_results[key]
        hist_df = data['historical_df']
        future_df = data['forecast_future_df']
        error_metrics = data['error_metrics']
        
        # 绘制实际值曲线（仅绘制一次）
        if not actual_plotted:
            train_df = hist_df[hist_df['split'] == 'Train']
            test_df = hist_df[hist_df['split'] == 'Test']
            fig.add_trace(go.Scatter(
                x=train_df['date'],
                y=train_df['actual'],
                mode='lines',
                name='Training Actual',
                line=dict(color='blue', width=2),
                legendgroup='Actual Data'
            ))
            fig.add_trace(go.Scatter(
                x=test_df['date'],
                y=test_df['actual'],
                mode='lines',
                name='Testing Actual',
                line=dict(color='red', width=2),
                legendgroup='Actual Data'
            ))
            train_end_date = train_df['date'].iloc[-1]
            test_start_date = test_df['date'].iloc[0]
            actual_plotted = True
        
        # 绘制测试集预测曲线
        if 'test_forecast' in hist_df.columns:
            fig.add_trace(go.Scatter(
                x=hist_df['date'],
                y=hist_df['test_forecast'],
                mode='lines',
                name=f"{model} Testing Forecast",
                line=dict(color=colors[idx % len(colors)], width=2),
                opacity=0.8,
                legendgroup=f"Model {idx + 1}"
            ))
        
        # 绘制未来预测曲线
        if not future_df.empty and 'final_forecast' in future_df.columns:
            fig.add_trace(go.Scatter(
                x=future_df['date'],
                y=future_df['final_forecast'],
                mode='lines',
                name=f"{model} Future Forecast",
                line=dict(color=colors[idx % len(colors)], width=2),
                opacity=0.8,
                legendgroup=f"Model {idx + 1}"
            ))
            test_end_date = hist_df['date'].iloc[-1]
        
        # 构造误差指标表格数据
        mae = round(error_metrics.get('MAE', 0), 2) if error_metrics.get('MAE') is not None else "N/A"
        mse = round(error_metrics.get('MSE', 0), 2) if error_metrics.get('MSE') is not None else "N/A"
        rmse = round(error_metrics.get('RMSE', 0), 2) if error_metrics.get('RMSE') is not None else "N/A"
        table_data.append({
            "Model": model,
            "MAE": mae,
            "MSE": mse,
            "RMSE": rmse
        })
    
    # 添加训练集与测试集分割线
    if train_end_date and test_start_date:
        fig.add_trace(go.Scatter(
            x=[train_end_date, train_end_date],
            y=[global_y_min, global_y_max],
            mode='lines',
            name='Train-Test Split',
            line=dict(color='black', dash='dash', width=3),
            showlegend=False
        ))
    
    # 添加测试集与未来预测分割线
    if test_end_date:
        fig.add_trace(go.Scatter(
            x=[test_end_date, test_end_date],
            y=[global_y_min, global_y_max],
            mode='lines',
            name='Test-Future Split',
            line=dict(color='black', dash='dash', width=3),
            showlegend=False
        ))
    
    title_text = f"{selected_city} - {selected_variable} Forecast (Model Comparison)"
    fig.update_layout(
        title=title_text,
        xaxis_title="Date",
        yaxis_title="Duration (units)",
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            title=None
        ),
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode="x unified",
        annotations=[
            dict(
                x=train_end_date,
                y=global_y_max + (global_y_max - global_y_min) * 0.05,
                xref="x",
                yref="y",
                text="Train-Test Split",
                showarrow=True,
                arrowhead=2,
                ax=0,
                ay=-40,
                font=dict(color="black")
            ),
            dict(
                x=test_end_date,
                y=global_y_max + (global_y_max - global_y_min) * 0.05,
                xref="x",
                yref="y",
                text="Test-Future Split",
                showarrow=True,
                arrowhead=2,
                ax=0,
                ay=-40,
                font=dict(color="black")
            )
        ]
    )
    
    return fig, table_data

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)

