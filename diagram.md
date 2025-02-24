```mermaid
graph TB
    subgraph Client Layer
        API[FastAPI Service]
        WC[Web Client]
    end

    subgraph Processing Layer
        GS[GeoServer]
        WPS[WPS Scripts]
        NM[NoiseModelling Core]
    end

    subgraph Calculation Layer
        EM[Emission Module]
        PM[Propagation Module]
        RT[Ray Tracing]
    end

    subgraph Data Layer
        PG[(PostGIS/H2)]
        SHP[Shapefile Storage]
    end

    WC --> API
    API --> GS
    GS --> WPS
    WPS --> NM
    NM --> EM
    NM --> PM
    NM --> RT
    EM --> PG
    PM --> PG
    RT --> PG
    PG --> SHP
```

```mermaid
graph TB
    subgraph "GeoServer Platform"
        WPS[WPS Services]
        DS[Data Store]
        GS_LIB[GeoServer Libraries]
        NM_LIB[NoiseModelling Libraries]
    end

    subgraph "Data Sources"
        Buildings[Building Data]
        Roads[Road Network]
        Terrain[DEM/Terrain]
        Receivers[Receiver Points]
    end

    subgraph "Processing"
        WPS --> NM_LIB
        NM_LIB --> Calc[Noise Calculation]
        DS --> NM_LIB
    end

    Buildings --> DS
    Roads --> DS
    Terrain --> DS
    Receivers --> DS
    
    Calc --> Results[Result Layers]
    Results --> DS
```
# WPS script integration approach

```mermaid
graph TB
    subgraph "Client Layer"
        style Client Layer fill:#98FB98,stroke:#006400
        API[FastAPI Service]
        style API fill:#7FFF00
        WC[WPS Client]
        style WC fill:#90EE90
    end

    subgraph "GeoServer Environment"
        style GeoServer Environment fill:#FFB6C1,stroke:#FF69B4
        subgraph "GeoServer Components"
            style GeoServer Components fill:#FFA07A
            WPS[WPS Service]
            style WPS fill:#FA8072
            GS[GeoServer Core]
            style GS fill:#F08080
            REST[REST API]
            style REST fill:#CD5C5C
        end

        subgraph "NoiseModelling Components"
            style NoiseModelling Components fill:#87CEEB
            NM[NoiseModelling Libraries]
            style NM fill:#ADD8E6
            CALC[Calculation Engine]
            style CALC fill:#B0E0E6
            EM[Emission Module]
            style EM fill:#B0C4DE
            PROP[Propagation Module]
            style PROP fill:#87CEEB
        end
    end

    subgraph "Data Store"
        style Data Store fill:#DDA0DD,stroke:#9370DB
        DS[(Spatial Database)]
        style DS fill:#DA70D6
        SHP[Shapefile Storage]
        style SHP fill:#BA55D3
        IN[Input Data]
        style IN fill:#9370DB
        OUT[Results]
        style OUT fill:#8A2BE2
    end

    IN ==>|"HTTP Request"| API
    API ==>|"WPS Request"| WC
    WC ==>|"HTTP"| REST
    WC ==>|"WPS"| WPS
    REST & WPS ==>|"Process"| GS
    GS ==>|"Execute"| NM
    NM ==>|"Calculate"| CALC
    CALC ==>|"Compute"| EM & PROP
    EM & PROP ==>|"Store"| DS
    DS ==>|"Save"| SHP
    DS ==>|"Return"| OUT

    classDef default fill:#f9f,stroke:#333,stroke-width:2px;
```


# direct Java classes interface (JNIUS) approach

```mermaid
graph TB
    subgraph "Python Layer" [Python Application Layer]
        style Python Layer fill:#98FB98,stroke:#006400
        API[FastAPI Service]
        style API fill:#7FFF00
        JB[JNius Bridge]
        style JB fill:#90EE90
        NMW[NoiseModelling Python Wrapper]
        style NMW fill:#98FB98
    end

    subgraph "Java Layer" [Java Component Layer]
        style Java Layer fill:#FFB6C1,stroke:#FF69B4
        subgraph "NoiseModelling Core" 
            style NoiseModelling Core fill:#FFA07A
            NMJ[NoiseModelling Libraries]
            style NMJ fill:#FA8072
            CALC[Calculation Engine]
            style CALC fill:#F08080
            EM[Emission Module]
            style EM fill:#CD5C5C
            PROP[Propagation Module]
            style PROP fill:#DC143C
        end
        JVM[Java Virtual Machine]
        style JVM fill:#FF69B4
    end

    subgraph "Data Layer"
        style Data Layer fill:#87CEEB,stroke:#4682B4
        IN[Input Data]
        style IN fill:#ADD8E6
        OUT[Results]
        style OUT fill:#B0E0E6
        STORE[(Data Storage)]
        style STORE fill:#87CEEB
    end

    IN ==>|"Data Input"| API
    API ==>|"Process"| NMW
    NMW ==>|"JVM Bridge"| JB
    JB ==>|"Java Call"| NMJ
    NMJ ==>|"Execute"| JVM
    JVM ==>|"Calculate"| CALC
    CALC ==>|"Compute"| EM
    CALC ==>|"Compute"| PROP
    EM & PROP ==>|"Store"| STORE
    STORE ==>|"Output"| OUT

    classDef default fill:#f9f,stroke:#333,stroke-width:2px;

```

## GeoServer

- necessary Using WPS interface
- spatial data management
- web service capabilities
- visualization features


## architecture

```mermaid
graph TD
    A[Groovy Scripts] --> B[Database Integration]
    A --> C[Java Components]
    B --> D[H2GIS Database]
    C --> E[Emission]
    C --> F[Pathfinder]
    C --> G[Propagation]

    subgraph Groovy Scripts
        A1[noise_level_from_traffic.groovy]
        A2[road_emission_from_traffic.groovy]
    end

    subgraph Java Components
        E1[LDENConfig]
        E2[LDENPropagationProcessData]
        F1[PropagationProcessPathData]
        G1[PowerUtils]
    end

    subgraph Database Integration
        B1[Open Connection]
        B2[Execute SQL Queries]
        B3[Retrieve Data]
        B4[Store Results]
    end

    subgraph H2GIS Database
        D1[Spatial Data]
        D2[Traffic Data]
        D3[Noise Maps]
    end

    A1 --> B1
    A1 --> B2
    A1 --> B3
    A1 --> B4
    A1 --> E1
    A1 --> E2
    A1 --> F1
    A1 --> G1

    A2 --> B1
    A2 --> B2
    A2 --> B3
    A2 --> B4
    A2 --> E1
    A2 --> E2
    A2 --> F1
    A2 --> G1
```