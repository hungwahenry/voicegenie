import pyaudio

def get_device_guide_text():
    p = pyaudio.PyAudio()
    output = []
    
    def log(msg=""):
        output.append(msg)
    
    log("AUDIO SETUP GUIDE")
    log("="*40)
    
    physical_mic = None
    cable_output = None
    physical_speaker = None
    cable_input = None

    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')

    # Scan Devices (Silent)
    for i in range(0, numdevices):
        dev = p.get_device_info_by_index(i)
        name = dev.get('name')
        if dev.get('maxInputChannels') > 0:
            if ('microphone' in name.lower() or 'realtek' in name.lower()) and 'array' in name.lower():
                physical_mic = {'id': i, 'name': name}
            if 'cable output' in name.lower():
                cable_output = {'id': i, 'name': name}
        
        if dev.get('maxOutputChannels') > 0:
            if 'speaker' in name.lower() or 'headphone' in name.lower() or 'realtek' in name.lower():
                physical_speaker = {'id': i, 'name': name}
            if 'cable input' in name.lower() and 'vb-audio' in name.lower():
                cable_input = {'id': i, 'name': name}

    log("\n1. TESTING MODE (Hear yourself)")
    log("-" * 40)
    log(f"• Input:  {physical_mic['name'] if physical_mic else 'Your Physical Mic'}")
    log(f"• Output: {physical_speaker['name'] if physical_speaker else 'Your Speakers/Headphones'}")
    
    log("\n2. LIVE CALL MODE (Discord, Telegram, etc)")
    log("-" * 40)
    log(f"• Input:  {physical_mic['name'] if physical_mic else 'Your Physical Mic'}")
    log(f"• Output: {cable_input['name'] if cable_input else 'CABLE Input (VB-Audio)'}")
    
    log("\n3. CHAT APP SETTINGS (In Discord/Telegram)")
    log("-" * 40)
    log(f"• Microphone: {cable_output['name'] if cable_output else 'CABLE Output (VB-Audio)'}")
    
    log("\n" + "="*40)
    if not cable_input or not cable_output:
        log("\n⚠ VB-CABLE NOT DETECTED!")
        log("Install from: vb-audio.com/Cable")

    p.terminate()
    return "\n".join(output)

if __name__ == "__main__":
    print(get_device_guide_text())
