from pathlib import Path
import jnius_config
import os

# Get absolute path to the lib directory
current_dir = Path(__file__).parent
lib_dir = (current_dir.parent / 'dist' / 'lib').resolve()

# Configure Java classpath
jnius_config.add_options('-Xmx4096m')
classpath = str(lib_dir / '*')
print(f"Setting classpath to: {classpath}")

# Debug: List all JAR files in the lib directory
for jar_file in lib_dir.glob('*.jar'):
    print(f"Found JAR: {jar_file.name}")

jnius_config.set_classpath(classpath)

from jnius import autoclass

# Test basic Java functionality first
print("\nTesting basic Java functionality:")
autoclass('java.lang.System').out.println('Hello world')

def test_noise_config():
    try:
        # Load NoiseModelling classes used in the Groovy script
        LDENConfig = autoclass('org.noise_planet.noisemodelling.jdbc.LDENConfig')
        LDENConfig_INPUT_MODE = autoclass('org.noise_planet.noisemodelling.jdbc.LDENConfig$INPUT_MODE')
        
        # Create LDENConfig instance
        lden_config = LDENConfig(LDENConfig_INPUT_MODE.INPUT_MODE_TRAFFIC_FLOW)
        
        # Configure like in Groovy script
        lden_config.setComputeLDay(True)
        lden_config.setComputeLEvening(True)
        lden_config.setComputeLNight(True)
        lden_config.setComputeLDEN(True)
        
        print("\nSuccessfully created and configured LDENConfig")
        return True
        
    except Exception as e:
        print(f"\nError in test_noise_config: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_noise_config()