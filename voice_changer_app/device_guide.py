import pyaudio

def inspect_audio_devices():
    p = pyaudio.PyAudio()
    
    print("\n" + "="*70)
    print("AUDIO DEVICE INSPECTION & CONFIGURATION GUIDE")
    print("="*70)
    
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')

    inputs = []
    outputs = []

    for i in range(0, numdevices):
        dev = p.get_device_info_by_index(i)
        name = dev.get('name')
        
        if dev.get('maxInputChannels') > 0:
            inputs.append({
                'id': i,
                'name': name,
                'channels': dev.get('maxInputChannels')
            })
        
        if dev.get('maxOutputChannels') > 0:
            outputs.append({
                'id': i,
                'name': name,
                'channels': dev.get('maxOutputChannels')
            })

    print("\n--- INPUT DEVICES (Microphones) ---")
    physical_mic = None
    cable_output = None
    
    for device in inputs:
        print(f"[ID: {device['id']}] {device['name']} ({device['channels']} ch)")
        
        # Identify physical mic
        if 'microphone' in device['name'].lower() or 'realtek' in device['name'].lower():
            if 'array' in device['name'].lower():
                physical_mic = device
        
        # Identify CABLE Output (for monitoring)
        if 'cable output' in device['name'].lower():
            cable_output = device
    
    print("\n--- OUTPUT DEVICES (Speakers / Virtual Cables) ---")
    physical_speaker = None
    cable_input = None
    
    for device in outputs:
        print(f"[ID: {device['id']}] {device['name']} ({device['channels']} ch)")
        
        # Identify physical speakers
        if 'speaker' in device['name'].lower() or 'headphone' in device['name'].lower() or 'realtek' in device['name'].lower():
            physical_speaker = device
        
        # Identify CABLE Input (the virtual mic that apps will use)
        if 'cable input' in device['name'].lower() and 'vb-audio' in device['name'].lower():
            cable_input = device

    print("\n" + "="*70)
    print("RECOMMENDED CONFIGURATIONS")
    print("="*70)
    
    print("\n🔧 MODE 1: TESTING (Hear yourself)")
    print("-" * 70)
    if physical_mic:
        print(f"✓ INPUT:  [ID: {physical_mic['id']}] {physical_mic['name']}")
    else:
        print("⚠ INPUT:  Select your physical microphone")
    
    if physical_speaker:
        print(f"✓ OUTPUT: [ID: {physical_speaker['id']}] {physical_speaker['name']}")
    else:
        print("⚠ OUTPUT: Select your Speakers/Headphones")
    
    print("\nWhat happens:")
    print("  • You speak into your real microphone")
    print("  • Voice is sent to ElevenLabs")
    print("  • Transformed voice plays through your speakers")
    print("  • YOU WILL HEAR the AI voice (with ~1-2s delay)")
    
    print("\n" + "-"*70)
    print("\n📞 MODE 2: PRODUCTION (Use in calls)")
    print("-" * 70)
    if physical_mic:
        print(f"✓ INPUT:  [ID: {physical_mic['id']}] {physical_mic['name']}")
    else:
        print("⚠ INPUT:  Select your physical microphone")
    
    if cable_input:
        print(f"✓ OUTPUT: [ID: {cable_input['id']}] {cable_input['name']}")
    else:
        print("⚠ OUTPUT: Select 'CABLE Input (VB-Audio Virtual C)'")
    
    print("\nWhat happens:")
    print("  • You speak into your real microphone")
    print("  • Voice is sent to ElevenLabs")
    print("  • Transformed voice is sent to CABLE Input")
    print("  • YOU WON'T HEAR anything (it goes to the virtual cable)")
    
    print("\n📱 In your chat app (Telegram/Discord/Signal):")
    if cable_output:
        print(f"  → Set Microphone to: CABLE Output")
    else:
        print("  → Set Microphone to: 'CABLE Output (VB-Audio Virtual C)'")
    print("  → Other people will hear the AI voice")
    
    print("\n" + "="*70)
    print("QUICK SUMMARY")
    print("="*70)
    print("\nTESTING:    Input = Real Mic  |  Output = Real Speakers")
    print("PRODUCTION: Input = Real Mic  |  Output = CABLE Input")
    print("            (Then set your chat app mic to CABLE Output)")
    print("\n" + "="*70 + "\n")

    p.terminate()

if __name__ == "__main__":
    inspect_audio_devices()
