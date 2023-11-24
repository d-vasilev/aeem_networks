import networkx as nx

import dash

from dash import html, dcc, ctx
from dash.dependencies import Input, Output, State

import plotly.graph_objects as go


def plotly_network(graph):
    pos = nx.spring_layout(graph, seed=42)

    def create_edge(edge):
        node1, node2, _ = edge

        return go.Scatter(
            x=[pos[node1][0], pos[node2][0]],
            y=[pos[node1][1], pos[node2][1]],
            line=dict(width=1, color="#00ff00"),
            hoverinfo="none",
            mode="lines",
        )

    edge_traces = [create_edge(edge) for edge in nx.to_edgelist(graph)]

    node_x = []
    node_y = []
    node_color = []
    node_text = []
    for node in graph.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_color.append("#00ff00" if graph.nodes[node]["optimal"] else "#ff0000")
        node_text.append(graph.nodes[node]["action"])

    node_trace = go.Scatter(
        name="",
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_text,
        textfont=dict(family="sans serif", size=24, color="Black"),
        # hoverinfo="skip",
        hoverinfo="text",
        # hovertemplate="utility:%{customdata:.2f}",
        marker=dict(
            # showscale=True,
            # colorscale options
            #'Greys' | 'YlGnBu' | 'Greens' | 'YlOrRd' | 'Bluered' | 'RdBu' |
            #'Reds' | 'Blues' | 'Picnic' | 'Rainbow' | 'Portland' | 'Jet' |
            #'Hot' | 'Blackbody' | 'Earth' | 'Electric' | 'Viridis' |
            reversescale=True,
            color=node_color,
            size=40,
            line_width=2,
        ),
    )

    fig = go.Figure(
        data=edge_traces + [node_trace],
        layout=go.Layout(
            showlegend=False,
            hovermode="closest",
            margin=dict(b=10, l=10, r=10, t=10),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )

    return fig


def create_graph(edge_list):
    graph = nx.from_edgelist(edge_list)
    for node in graph.nodes():
        graph.nodes[node]["action"] = 1
    return graph


def create_graph_coh():
    edge_list_coh = [
        (0, 1),
        (0, 2),
        (0, 3),
        (1, 2),
        (1, 4),
        (2, 4),
        (3, 4),
        (2, 5),
        (4, 5),
        (6, 3),
        (7, 5),
        (6, 7),
        (7, 8),
        (6, 9),
        (8, 9),
        (10, 8),
        (10, 9),
        (11, 10),
        (11, 9),
        (11, 8),
    ]
    return create_graph(edge_list_coh)


def description_card():
    """
    :return: A Div containing dashboard title & descriptions.
    """
    return html.Div(
        id="description-card",
        children=[
            html.H5("Network Games"),
            html.H3("Cordination Game Demo"),
            html.Div(
                id="intro",
                children="Explore network games action coordination simulations. Specify coordination threshold",
            ),
        ],
    )


def generate_control_card():
    """
    :return: A Div containing controls for graphs.
    """
    return html.Div(
        id="control-card",
        children=[
            dcc.Store(id="graph"),
            html.Br(),
            html.P("Coordination threshold"),
            dcc.Input(
                id="coor-thresh", type="number", min=0, max=1, value=0.5, step=0.1
            ),
            html.Br(),
        ],
    )


def create_net_games_coh_app(app):
    app.layout = html.Div(
        id="app-container",
        style={"display": "flex"},
        children=[
            html.Div(
                id="left-column",
                style={"width": "30.6666666667%"},
                children=[description_card(), generate_control_card()],
            ),
            # Right column
            html.Div(
                id="right-column",
                style={"width": "65.3333333333%"},
                children=[
                    html.Div(
                        children=[
                            html.H5("Network"),
                            dcc.Graph(id="network"),  # , style={"height": "250px"}),
                        ],
                    ),
                ],
            ),
        ],
    )

    @app.callback(
        Output("network", "figure"),
        [
            Input("graph", "data"),
        ],
    )
    def update_network(data):
        graph = nx.node_link_graph(data)
        return plotly_network(graph)

    @app.callback(
        Output("graph", "data"),
        [
            Input("network", "clickData"),
            Input("coor-thresh", "value"),
        ],
        State("graph", "data"),
    )
    def update_graph(click_data, threshold, data):
        ctx_id = ctx.triggered_id
        if ctx_id == "network":
            node_id = click_data["points"][0]["pointNumber"]
            graph = nx.node_link_graph(data)
            graph.nodes[node_id]["action"] = 1 - graph.nodes[node_id]["action"]
        elif ctx_id in ["coor-thresh"]:
            graph = nx.node_link_graph(data)
        else:
            graph = create_graph_coh()

        for node in graph.nodes():
            neighbors = list(graph.neighbors(node))
            numb_nghbr_1 = sum([1 for x in neighbors if graph.nodes[x]["action"] == 1])
            numb_nghbr_all = sum([1 for _ in neighbors])
            graph.nodes[node]["util_0"] = 0
            graph.nodes[node]["util_1"] = (
                1 if numb_nghbr_1 > threshold * numb_nghbr_all else -1
            )

            graph.nodes[node]["optimal"] = (
                (graph.nodes[node]["action"] == 1)
                and (graph.nodes[node]["util_1"] > graph.nodes[node]["util_0"])
            ) or (
                (graph.nodes[node]["action"] == 0)
                and (graph.nodes[node]["util_1"] < graph.nodes[node]["util_0"])
            )

        return nx.node_link_data(graph)


# Run the server
if __name__ == "__main__":
    app = dash.Dash(
        __name__,
        meta_tags=[
            {"name": "viewport", "content": "width=device-width, initial-scale=1"}
        ],
    )
    create_net_games_coh_app(app)
    app.run_server(debug=True)
