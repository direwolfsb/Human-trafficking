document.addEventListener('DOMContentLoaded', function() {
    // Example trafficking data (replace with real data)
    // Format: country code -> statistics
    const traffickingData = {
        "USA": { victims: 14500, description: "One of the largest destinations for trafficking victims" },
        "IND": { victims: 8000000, description: "Highest number of victims globally" },
        "CHN": { victims: 3200000, description: "Significant internal and cross-border trafficking" },
        "PAK": { victims: 2100000, description: "High prevalence of bonded labor" },
        "BGD": { victims: 1500000, description: "Source country for labor and sex trafficking" },
        "RUS": { victims: 794000, description: "Significant source and destination country" },
        "NGA": { victims: 1400000, description: "Major source country in Africa" },
        "IDN": { victims: 1220000, description: "Notable for forced labor issues" },
        "COL": { victims: 160000, description: "Affected by conflict-related trafficking" },
        "THA": { victims: 610000, description: "Hub for trafficking in Southeast Asia" },
        "MEX": { victims: 376800, description: "Transit and source country" },
        "PHL": { victims: 784000, description: "Major source country for labor trafficking" },
        "UKR": { victims: 260000, description: "Source country with conflict vulnerability" },
        "GHA": { victims: 133000, description: "Child labor and trafficking issues" },
        "MYS": { victims: 212000, description: "Destination for regional trafficking victims" },
        "CAN": { victims: 6500, description: "Destination and transit country" },
        "BRA": { victims: 369000, description: "Internal trafficking and forced labor" },
        "ZAF": { victims: 155000, description: "Regional hub in Southern Africa" },
        "FRA": { victims: 13000, description: "Destination for European trafficking" },
        "DEU": { victims: 167000, description: "Transit and destination in Europe" },
        "GBR": { victims: 136000, description: "Destination with increasing cases" },
        "ITA": { victims: 129600, description: "Entry point for trafficking into Europe" },
        "AUS": { victims: 15000, description: "Destination country in Oceania" }
    };

    // Create tooltip element directly in HTML for better reliability
    const mapContainer = document.querySelector('.login-image');
    const tooltipElement = document.createElement('div');
    tooltipElement.className = 'map-tooltip';
    tooltipElement.style.display = 'none';
    document.body.appendChild(tooltipElement);

    // Make the map container cover the full login-image area
    const container = document.getElementById('trafficking-map');
    container.style.position = 'absolute';
    container.style.top = '0';
    container.style.left = '0';
    container.style.width = '100%';
    container.style.height = '100%';
    container.style.zIndex = '1';
    
    // Make the map-container a background
    const mapInfoContainer = document.querySelector('.map-container');
    if (mapInfoContainer) {
        mapInfoContainer.style.position = 'absolute';
        mapInfoContainer.style.top = '0';
        mapInfoContainer.style.left = '0';
        mapInfoContainer.style.width = '100%';
        mapInfoContainer.style.height = '100%';
        mapInfoContainer.style.margin = '0';
        mapInfoContainer.style.padding = '0';
        mapInfoContainer.style.background = 'none';
    }
    
    // Put login image text on top of the map
    const loginText = document.querySelector('.login-image h1, .login-image p');
    if (loginText) {
        loginText.style.position = 'relative';
        loginText.style.zIndex = '2';
    }

    // Map dimensions - Full size
    const width = mapContainer ? mapContainer.offsetWidth : 800;
    const height = mapContainer ? mapContainer.offsetHeight : 500;

    // Create SVG that fills the container
    const svg = d3.select("#trafficking-map")
        .append("svg")
        .attr("width", "100%")
        .attr("height", "100%")
        .attr("viewBox", [0, 0, width, height])
        .attr("preserveAspectRatio", "xMidYMid meet")
        .style("background-color", "rgba(0, 0, 0, 0.6)");

    // Create a group for the map
    const g = svg.append("g");

    // Create a color scale based on victim numbers
    const colorScale = d3.scaleSequential(d3.interpolateReds)
        .domain([0, 1000000]);  // Adjust domain based on your data range

    // Load world map data
    d3.json("https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson")
        .then(function(data) {
            // Draw the map
            const countries = g.selectAll("path")
                .data(data.features)
                .join("path")
                .attr("fill", d => {
                    const countryCode = d.properties.iso_a3;
                    return traffickingData[countryCode] ? 
                        colorScale(traffickingData[countryCode].victims) : 
                        "rgba(45, 46, 48, 0.5)";
                })
                .attr("d", d3.geoPath()
                    .projection(d3.geoMercator()
                        .scale(width / 7)
                        .center([0, 20])
                        .translate([width / 2, height / 2]))
                )
                .attr("class", "country")
                .style("stroke", "#141517")
                .style("stroke-width", 0.5);
            
            // Handle hover events using manual DOM events for better reliability
            countries.on("mouseover", function(event, d) {
                const countryCode = d.properties.iso_a3;
                if (traffickingData[countryCode]) {
                    d3.select(this)
                        .style("stroke", "#ffcc00")
                        .style("stroke-width", 2)
                        .style("cursor", "pointer");
                    
                    // Set tooltip content
                    tooltipElement.innerHTML = `
                        <strong>${d.properties.name}</strong><br/>
                        Estimated victims: ${traffickingData[countryCode].victims.toLocaleString()}<br/>
                        ${traffickingData[countryCode].description}
                    `;
                    
                    // Show and position tooltip
                    tooltipElement.style.display = 'block';
                    tooltipElement.style.opacity = '1';
                    tooltipElement.style.left = (event.pageX + 15) + 'px';
                    tooltipElement.style.top = (event.pageY - 30) + 'px';
                }
            })
            .on("mousemove", function(event) {
                // Update tooltip position while moving
                tooltipElement.style.left = (event.pageX + 15) + 'px';
                tooltipElement.style.top = (event.pageY - 30) + 'px';
            })
            .on("mouseout", function() {
                d3.select(this)
                    .style("stroke", "#141517")
                    .style("stroke-width", 0.5);
                
                // Hide tooltip
                tooltipElement.style.opacity = '0';
                setTimeout(() => {
                    tooltipElement.style.display = 'none';
                }, 300);
            });

            // Add a title overlay at the bottom
            svg.append("text")
                .attr("x", width / 2)
                .attr("y", height - 20)
                .attr("text-anchor", "middle")
                .attr("fill", "white")
                .attr("font-size", "14px")
                .text("Hover over countries to see human trafficking statistics");
        })
        .catch(function(error) {
            console.error("Error loading map data:", error);
            container.innerHTML = `<div style="color:red;padding:20px;">Error loading map data</div>`;
        });
});