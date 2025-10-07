# NoiseProcesses

A python wrapper for NoiseModelling v4.0.

## Acknowledgment

This project is derived from the NoiseModelling project, an open-source tool for environmental noise mapping.

NoiseModelling is developed by the DECIDE team from the Lab-STICC (CNRS) and the Mixt Research Unit in Environmental Acoustics (Université Gustave Eiffel). You can find more information about NoiseModelling at [http://noise-planet.org/noisemodelling.html](http://noise-planet.org/noisemodelling.html).

NoiseModelling is distributed under the GNU General Public License v3.0.


## For Developers
### Python project setup 

This project uses a copier template for the basic project setup. 

```
# initial setup was done with:
copier copy git+https://USERNAME@bitbucket.org/geowerkstatt-hamburg/python_project_template --trust --vcs-ref main .
# !You dont need to do this again!
```

To update this projects underlying template:

```
# update
copier update . --trust
```

### Java setup

Use the `java_setup.sh` file to install java dependencies. Run:

```bash
# make it executable
chmod +x java_setup.sh

# run it
./setup.sh

# after that, source your bashrc or restart your terminal:
source ~/.bashrc

# verify your environment
echo $JAVA_HOME
java -version
mvn -version
```

### Build the java-based NoiseModelling library

To build run:

```
make check-java
make dist
```

## Notes

### Calculation of receivers along building facades

```mermaid
flowchart TD
    A[Start: Building Polygon]
    B{Isolated or Surrounded?}
    C1[Isolated: No nearby buildings]
    C2[Surrounded: Overlaps with other buildings]
    D1[tmp_receivers_lines: Create receiver line]
    D2[tmp_receivers_lines: Create receiver line]
    E1[tmp_relation_screen_building: No intersection with other buildings]
    E2[tmp_relation_screen_building: Intersects with other buildings]
    F1[TMP_SCREENS_MERGE: Use original receiver line]
    F2[tmp_screen_truncated: Truncate receiver line]
    G2[TMP_SCREENS_MERGE: Use truncated receiver line]
    H[TMP_SCREENS: Split line into points]
    I[RECEIVERS: Store receiver points]

    A --> B
    B --> C1
    B --> C2
    C1 --> D1
    C2 --> D2
    D1 --> E1
    D2 --> E2
    E1 --> F1
    E2 --> F2
    F2 --> G2
    F1 --> H
    G2 --> H
    H --> I
```

# LICENSE
This software is based on and uses components from [NoiseModelling](https://github.com/Universite-Gustave-Eiffel/NoiseModelling/) and is licenced under GPLv3.