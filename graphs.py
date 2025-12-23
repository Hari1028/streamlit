import plotly.express as px

def render_line_chart(df, x, y, title="Trend Analysis"):
    """Template 1: Line Chart for Time Series & Spikes"""
    try:
        return px.line(df, x=x, y=y, title=title, template="plotly_dark")
    except Exception as e:
        return px.bar(title=f"Error rendering Line Chart: {e}")

def render_bar_chart(df, x, y, title="Category Comparison"):
    """Template 2: Bar Chart for Counts & Nulls"""
    try:
        return px.bar(df, x=x, y=y, title=title, template="plotly_dark")
    except Exception as e:
        return px.bar(title=f"Error rendering Bar Chart: {e}")

def render_scatter_chart(df, x, y, color=None, title="Correlation Check"):
    """Template 3: Scatter Plot for Outliers"""
    try:
        return px.scatter(df, x=x, y=y, color=color, title=title, template="plotly_dark")
    except Exception as e:
        return px.bar(title=f"Error rendering Scatter Chart: {e}")

def render_histogram(df, x, title="Distribution Analysis"):
    """Template 4: Histogram for Price Distributions"""
    try:
        return px.histogram(df, x=x, title=title, template="plotly_dark")
    except Exception as e:
        return px.bar(title=f"Error rendering Histogram: {e}")

def graph_factory(df, config):
    """
    The Router: Receives JSON config and picks the right template.
    """
    graph_type = config.get('type')
    
    if graph_type == 'line':
        return render_line_chart(df, config['x'], config['y'], config.get('title'))
    elif graph_type == 'bar':
        return render_bar_chart(df, config['x'], config['y'], config.get('title'))
    elif graph_type == 'scatter':
        return render_scatter_chart(df, config['x'], config['y'], config.get('color'), config.get('title'))
    elif graph_type == 'histogram':
        return render_histogram(df, config['x'], config.get('title'))
    else:
        return None