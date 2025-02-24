# NoiseProcesses

A python wrapper for NoiseModelling v4.

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