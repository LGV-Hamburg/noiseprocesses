#!/bin/bash

# Exit on error
set -e

echo "Installing Java 11 and Maven..."

# Update package list
sudo apt-get update

# Install Java 11
sudo apt-get install -y openjdk-11-jdk

# Install Maven
sudo apt-get install -y maven

# Verify installations
echo "Verifying installations..."

# Check Java version
java -version

# Check Maven version
mvn -version

# Set JAVA_HOME if not already set
if [ -z "$JAVA_HOME" ]; then
    echo "export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64" >> ~/.bashrc
    echo "export PATH=\$JAVA_HOME/bin:\$PATH" >> ~/.bashrc
fi

# Make the script executable after creating it:
chmod +x setup.sh