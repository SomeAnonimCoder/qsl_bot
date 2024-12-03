from flask import Flask, render_template
import pandas as pd
import sqlalchemy
import plotly.express as px
import plotly.graph_objects as go
import json
import plotly


app = Flask(__name__)

SQLALCHEMY_DATABASE_URI = 'mysql://bot_user:your_password@localhost/TelegramBot?unix_socket=/run/mysqld/mysqld.sock'

engine = sqlalchemy.create_engine(SQLALCHEMY_DATABASE_URI)




@app.route("/")
def dashboard():
    # Query to get the last 50 contacts
    query = """
    SELECT 
        c1.id AS user_contact_id,
        c2.id AS correspondent_contact_id,
        u1.username AS user,
        u2.username AS correspondent,
        c1.timestamp AS user_timestamp,
        c2.timestamp AS correspondent_timestamp,
        ST_X(c1.location) AS user_latitude,
        ST_Y(c1.location) AS user_longitude,
        ST_X(c2.location) AS correspondent_latitude,
        ST_Y(c2.location) AS correspondent_longitude,
        b1.band_name AS user_band,
        b2.band_name AS correspondent_band
    FROM Contacts c1
    JOIN Contacts c2 ON c1.contact_with_id = c2.user_id AND c2.contact_with_id = c1.user_id
    JOIN Users u1 ON c1.user_id = u1.id
    JOIN Users u2 ON c2.user_id = u2.id
    LEFT JOIN Bands b1 ON c1.band_id = b1.id
    LEFT JOIN Bands b2 ON c2.band_id = b2.id
    WHERE ABS(TIMESTAMPDIFF(SECOND, c1.timestamp, c2.timestamp)) = (
        SELECT MIN(ABS(TIMESTAMPDIFF(SECOND, c1.timestamp, c.timestamp)))
        FROM Contacts c
        WHERE c.user_id = c2.user_id AND c.contact_with_id = c1.user_id
    )
    AND ABS(TIMESTAMPDIFF(SECOND, c1.timestamp, c2.timestamp)) < 1000
    AND c1.id < c2.id
    ORDER BY c1.timestamp DESC
    LIMIT 50;
    """
    df = pd.read_sql(query, engine)

    # Data for pie charts
    contacts_by_band = df["user_band"].value_counts().reset_index()
    contacts_by_band.columns = ["Band", "Count"]

    contacts_by_user = pd.concat([df["user"], df["correspondent"]]).value_counts().reset_index()
    contacts_by_user.columns = ["User", "Count"]

    # Generate pie charts
    pie_chart_band = px.pie(
        contacts_by_band, 
        names="Band", 
        values="Count", 
        title="Contacts by Band", 
        color_discrete_sequence=px.colors.sequential.Viridis
    )
    pie_chart_user = px.pie(
        contacts_by_user, 
        names="User", 
        values="Count", 
        title="Contacts by User", 
        color_discrete_sequence=px.colors.sequential.Viridis
    )

    # Convert pie charts to JSON
    chart_band_json = json.dumps(pie_chart_band, cls=plotly.utils.PlotlyJSONEncoder)
    chart_user_json = json.dumps(pie_chart_user, cls=plotly.utils.PlotlyJSONEncoder)


    map_fig = go.Figure()

    # Add lines and markers for each contact
    for _, row in df.iterrows():
        # Add line for contact
        map_fig.add_trace(
            go.Scattergeo(
                lon=[row["user_longitude"], row["correspondent_longitude"]],
                lat=[row["user_latitude"], row["correspondent_latitude"]],
                mode="lines",
                line=dict(width=2, color="blue"),
                name=f"{row['user']} to {row['correspondent']}",
            )
        )
        # Add markers for user location
        map_fig.add_trace(
            go.Scattergeo(
                lon=[row["user_longitude"]],
                lat=[row["user_latitude"]],
                mode="markers",
                marker=dict(size=6, color="red", symbol="circle"),
                name=row["user"],
            )
        )
        # Add markers for correspondent location
        map_fig.add_trace(
            go.Scattergeo(
                lon=[row["correspondent_longitude"]],
                lat=[row["correspondent_latitude"]],
                mode="markers",
                marker=dict(size=6, color="green", symbol="circle"),
                name=row["correspondent"],
            )
        )

    # Update layout to make the map wider and adjust appearance
    # Update layout for OpenStreetMap
    map_fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        height=600,  # Set map height
        width=1200,  # Set map width
        title="Contacts Map (Free OSM)"
    )
    map_fig.update_layout(map_style="dark")
    # focus point
    lat_foc = 40.177940
    lon_foc = 44.504754
    map_fig.update_layout(
        geo = dict(
            projection_scale=5000, #this is kind of like zoom
            center=dict(lat=lat_foc, lon=lon_foc), # this will center on the point
        ))    
    map_json = json.dumps(map_fig, cls=plotly.utils.PlotlyJSONEncoder)    # Generate map with lines for contacts

    # Render template
    return render_template(
        "dashboard.html",
        table=df.to_html(classes="table table-striped", index=False),
        chart_band=chart_band_json,
        chart_user=chart_user_json,
        map_json=map_json,
    )
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
