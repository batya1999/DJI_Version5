DJI Mobile SDK V5 Enhanced for DJI Mini 3 with Remote Control via WebSocket
Overview

This project extends the DJI Mobile SDK (MSDK) V5 to enable remote control of the DJI Mini 3 drone. The setup consists of an Android app that acts as a bridge to pass commands from a WebSocket server to the drone's remote controller (RC). It allows seamless integration for remote operations over a local server.
Key Features

    Remote Control Support: Commands are sent from the server to the drone via the Android app.
    WebSocket Communication: Enables local server-based control for enhanced flexibility.
    Enhanced Compatibility: Built specifically for DJI Mini 3 using MSDK V5 (version 5.11.0).

How It Works

    Android App: Functions as a communication bridge between the WebSocket server and the DJI Mini 3 RC.
    WebSocket Server: Handles incoming control commands (e.g., movement directions) and passes them to the app.
    Drone Control: The app uses DJI MSDK V5 APIs to relay commands to the drone's RC.

Supported Commands

    moveDrone(roll, throttle, yaw, pitch)- gets float values between 0-1

Setup Guide
Prerequisites

    DJI Mini 3 drone.
    Android device with DJI MSDK V5-compatible app.
    Local WebSocket server.

Integration Steps

    Clone this repository.
    Set up the WebSocket server to handle drone control commands.
    Deploy the Android app on a compatible device.
    Connect the Android device and server to the same local network.
    Use the WebSocket server to send commands, and the app will relay them to the drone.

Dependencies

    DJI Mobile SDK V5: Provides APIs for drone control.
        Add the following dependencies to your build.gradle file:

        implementation 'com.dji:dji-sdk-v5-aircraft:5.11.0'
        compileOnly 'com.dji:dji-sdk-v5-aircraft-provided:5.11.0'
        runtimeOnly 'com.dji:dji-sdk-v5-networkImp:5.11.0'

License

This project integrates the DJI Mobile SDK, which is subject to LGPL v2.1. The sample code provided in this repository is released under the MIT License.
Support

For further assistance, refer to:

    DJI Developer Forum
    MSDK Documentation
