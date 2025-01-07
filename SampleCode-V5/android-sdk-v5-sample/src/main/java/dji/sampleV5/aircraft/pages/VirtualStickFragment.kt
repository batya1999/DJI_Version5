package dji.sampleV5.aircraft.pages

import android.os.Bundle
import dji.sdk.keyvalue.value.common.LocationCoordinate2D
import dji.v5.ux.mapkit.core.models.DJILatLng
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.activityViewModels
import dji.sampleV5.aircraft.databinding.FragVirtualStickPageBinding
import dji.sampleV5.aircraft.keyvalue.KeyValueDialogUtil
import dji.sampleV5.aircraft.models.BasicAircraftControlVM
import dji.sampleV5.aircraft.models.SimulatorVM
import dji.sampleV5.aircraft.models.VirtualStickVM
import dji.sampleV5.aircraft.util.Helper
import dji.sampleV5.aircraft.util.ToastUtils
import dji.sampleV5.aircraft.util.Util
import dji.sampleV5.aircraft.virtualstick.OnScreenJoystick
import dji.sampleV5.aircraft.virtualstick.OnScreenJoystickListener
import dji.sdk.keyvalue.value.common.EmptyMsg
import dji.sdk.keyvalue.value.flightcontroller.VirtualStickFlightControlParam
import dji.sdk.keyvalue.value.rtkmobilestation.GNSSType
import dji.v5.common.callback.CommonCallbacks
import dji.v5.common.error.IDJIError
import dji.v5.manager.aircraft.virtualstick.Stick
import dji.v5.utils.common.JsonUtil

import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.util.Locale
import kotlin.math.abs

class VirtualStickFragment : DJIFragment() {

    private val basicAircraftControlVM: BasicAircraftControlVM by activityViewModels()
    private val virtualStickVM: VirtualStickVM by activityViewModels()
    private val simulatorVM: SimulatorVM by activityViewModels()
    private var binding: FragVirtualStickPageBinding? = null
    private val derivation: Double = 0.02
    private val client = OkHttpClient()
    private lateinit var webSocket: WebSocket
    private val constantThrottle = 0.5f
    private val TAKEOFF_HEIGHT: Float = 1.2f
//    private val gpsAntenna1TextView: TextView = findViewById(R.id.textview_gps_antenna_1)



    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        binding = FragVirtualStickPageBinding.inflate(inflater, container, false)
        return binding?.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        binding?.widgetHorizontalSituationIndicator?.setSimpleModeEnable(false)
        initBtnClickListener()
        initStickListener()
        virtualStickVM.listenRCStick()
        virtualStickVM.currentSpeedLevel.observe(viewLifecycleOwner) {
            updateVirtualStickInfo()
        }
        virtualStickVM.useRcStick.observe(viewLifecycleOwner) {
            updateVirtualStickInfo()
        }
        virtualStickVM.currentVirtualStickStateInfo.observe(viewLifecycleOwner) {
            updateVirtualStickInfo()
        }
        virtualStickVM.stickValue.observe(viewLifecycleOwner) {
            updateVirtualStickInfo()
        }
        virtualStickVM.virtualStickAdvancedParam.observe(viewLifecycleOwner) {
            updateVirtualStickInfo()
        }
        simulatorVM.simulatorStateSb.observe(viewLifecycleOwner) {
            binding?.simulatorStateInfoTv?.text = it
        }
        connectWebSocket()
//        LstartLive()
    }

    private fun sendMessageToServer(message: String) {
        // Ensure the WebSocket is open before sending the message
        if (::webSocket.isInitialized && webSocket.send(message)) {
            println("Message sent: $message")
        } else {
            println("Failed to send message: $message")
        }
    }

    // Connect to the WebSocket server
    private fun connectWebSocket() {
        val request = Request.Builder().url("ws://192.168.8.117:5000").build()
        val listener = object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                super.onOpen(webSocket, response)
                // WebSocket opened successfully
                ToastUtils.showToast("WebSocket connected")
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                super.onMessage(webSocket, text)
                println("Received message: $text")
                mainHandler.post {
                    handleServerMessage(text) // Process commands from the server
                }
            }
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                super.onFailure(webSocket, t, response)
                // Handle failure
                ToastUtils.showToast("WebSocket connection failed: ${t.message}")
            }
        }
        webSocket = client.newWebSocket(request, listener)
    }
    private fun showDroneLocation(latLng: DJILatLng?) {

        val latitude = latLng?.latitude
        val longitude = latLng?.longitude
        val altitude = latLng?.altitude
        val accuracy = latLng?.accuracy

        println("Drone Location:")
        println("Latitude: $latitude")
        println("Longitude: $longitude")
        println("Altitude: $altitude meters")
        println("Accuracy: $accuracy meters")
        val takeOffHeightString = Util.getHeight(context)
        val quickinfo = simulatorVM.quickInfo

        val height = view?.height
        ToastUtils.showToast("height: $height, $takeOffHeightString")
        ToastUtils.showToast("quickInfo: $quickinfo")



    }
    private fun getGPS(){
        val locationGPS = GNSSType.GPS
        ToastUtils.showToast("GPS location: $locationGPS")
    }
    private fun getHeight(){
        val takeOffHeightString = Util.getHeight(context)
        val height = view?.height
        ToastUtils.showToast("height: $height, $takeOffHeightString")
    }


    // Handle server response and act accordingly
    private fun handleServerMessage(text: String) {
        val command = text.trim().lowercase(Locale.getDefault())
        if (command.startsWith("movedrone:")) {
            val parameters = command.substringAfter("movedrone:").trim()
            val commandParts = parameters.split(",").map { it.trim().toFloatOrNull() }
            if (commandParts.size == 4 && commandParts.all { it != null }) {
                val (roll, throttle, yaw, pitch) = commandParts.map { it!! } // Unwrap non-null values
                moveDrone(roll, throttle, yaw, pitch)
            } else {
                ToastUtils.showToast("Invalid moveDrone parameters")
            }
        } else {
            when (command) {
                "yaw+" -> adjustYaw(0.1f)
                "yaw-" -> adjustYaw(-0.1f)
                "right" -> moveRight(0.05f)
                "left" -> moveLeft(0.05f)
                "takeoff" -> initiateTakeoff()
                "h" -> showHeight()
                "s" -> stopDrone()
                "land" -> landDrone()
                "enable" -> enableVirtualStick()
                "disable" -> disableVirtualStick()
                "forward" -> moveForward(0.05f)
                "backward" -> moveBackward(0.05f)
                "up" -> moveUp(0.1f)
                "down" -> moveDown(0.1f)
                else -> ToastUtils.showToast("Unknown command from server: $text")
            }
        }
    }



    private fun initiateTakeoff() {
        basicAircraftControlVM.startTakeOff(object :
            CommonCallbacks.CompletionCallbackWithParam<EmptyMsg> {
            override fun onSuccess(t: EmptyMsg?) {
                ToastUtils.showToast("Takeoff initiated successfully.")
            }

            override fun onFailure(error: IDJIError) {
                ToastUtils.showToast("Error initiating takeoff: $error")
            }
        })
    }
    private fun adjustYaw(yawIncrement: Float) {
        // Only adjust yaw; throttle should remain zero to prevent forward movement
        virtualStickVM.setLeftPosition(
            (yawIncrement * Stick.MAX_STICK_POSITION_ABS).toInt(),
            0 // Neutral throttle for in-place rotation
        )
    }
    private fun moveForward(speed: Float) {
        // Adjust pitch for forward movement; roll remains neutral
        virtualStickVM.setRightPosition(
            0, // Neutral roll
            (speed * Stick.MAX_STICK_POSITION_ABS).toInt() // positive pitch for forward movement

        )
//        moveDrone(roll = 0f, throttle = 0f, yaw = 0f, pitch = speed)
    }

    private fun moveBackward(speed: Float) {
        // Adjust pitch for backward movement; roll remains neutral
        virtualStickVM.setRightPosition(
            0, // Neutral roll
            (-speed * Stick.MAX_STICK_POSITION_ABS).toInt() // negative pitch for backward movement
        )
//        moveDrone(roll = 0f, throttle = 0f, yaw = 0f, pitch = -speed)
    }
    private fun moveUp(speed: Float) {
        // Adjust throttle for upward movement; yaw remains neutral
        virtualStickVM.setLeftPosition(
            0, // Neutral yaw
            (speed * Stick.MAX_STICK_POSITION_ABS).toInt() // Positive throttle for upward movement
        )
    }

    private fun moveDown(speed: Float) {
        // Adjust throttle for downward movement; yaw remains neutral
        virtualStickVM.setLeftPosition(
            0, // Neutral yaw
            (-speed * Stick.MAX_STICK_POSITION_ABS).toInt() // Negative throttle for downward movement
        )
    }


    // Enable virtual stick
    private fun enableVirtualStick() {
        virtualStickVM.enableVirtualStick(object : CommonCallbacks.CompletionCallback {
            override fun onSuccess() {
                ToastUtils.showToast("Virtual Stick enabled.")
            }

            override fun onFailure(error: IDJIError) {
                ToastUtils.showToast("Error enabling virtual stick: $error")
            }
        })
    }

    // Disable virtual stick
    private fun disableVirtualStick() {
        virtualStickVM.disableVirtualStick(object : CommonCallbacks.CompletionCallback {
            override fun onSuccess() {
                ToastUtils.showToast("Virtual Stick disabled.")
            }

            override fun onFailure(error: IDJIError) {
                ToastUtils.showToast("Error disabling virtual stick: $error")
            }
        })
    }

    private fun landDrone() {
        basicAircraftControlVM.startLanding(object :
            CommonCallbacks.CompletionCallbackWithParam<EmptyMsg> {
            override fun onSuccess(t: EmptyMsg?) {
                ToastUtils.showToast("Landing initiated successfully.")
            }

            override fun onFailure(error: IDJIError) {
                ToastUtils.showToast("Error initiating landing: $error")
            }
        })
    }

    private fun initBtnClickListener() {
        binding?.btnEnableVirtualStick?.setOnClickListener {
            virtualStickVM.enableVirtualStick(object : CommonCallbacks.CompletionCallback {
                override fun onSuccess() {
                    ToastUtils.showToast("enableVirtualStick success.")
                }

                override fun onFailure(error: IDJIError) {
                    ToastUtils.showToast("enableVirtualStick error, $error")
                }
            })
        }
        binding?.btnDisableVirtualStick?.setOnClickListener {
            virtualStickVM.disableVirtualStick(object : CommonCallbacks.CompletionCallback {
                override fun onSuccess() {
                    ToastUtils.showToast("disableVirtualStick success.")
                }

                override fun onFailure(error: IDJIError) {
                    ToastUtils.showToast("disableVirtualStick error, $error")
                }
            })
        }
//        binding?.btnSimulateStickClick?.setOnClickListener {
//            // Call the simulateStickClick function when the button is clicked
//            simulateForwardClick(isLeftStick = true, durationMillis = 1000)
//        }


        binding?.btnSetVirtualStickSpeedLevel?.setOnClickListener {
            val speedLevels = doubleArrayOf(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
            initPopupNumberPicker(Helper.makeList(speedLevels)) {
                virtualStickVM.setSpeedLevel(speedLevels[indexChosen[0]])
                resetIndex()
            }
        }
        binding?.btnTakeOff?.setOnClickListener {
            basicAircraftControlVM.startTakeOff(object :
                CommonCallbacks.CompletionCallbackWithParam<EmptyMsg> {
                override fun onSuccess(t: EmptyMsg?) {
                    ToastUtils.showToast("start takeOff onSuccess.")
                }

                override fun onFailure(error: IDJIError) {
                    ToastUtils.showToast("start takeOff onFailure,$error")
                }
            })
        }
        binding?.btnLanding?.setOnClickListener {
            basicAircraftControlVM.startLanding(object :
                CommonCallbacks.CompletionCallbackWithParam<EmptyMsg> {
                override fun onSuccess(t: EmptyMsg?) {
                    ToastUtils.showToast("start landing onSuccess.")
                }

                override fun onFailure(error: IDJIError) {
                    ToastUtils.showToast("start landing onFailure,$error")
                }
            })
        }
        binding?.btnUseRcStick?.setOnClickListener {
            virtualStickVM.useRcStick.value = virtualStickVM.useRcStick.value != true
            if (virtualStickVM.useRcStick.value == true) {
                ToastUtils.showToast(
                    "After it is turned on," +
                            "the joystick value of the RC will be used as the left/ right stick value"
                )
            }
        }
        binding?.btnSetVirtualStickAdvancedParam?.setOnClickListener {
            KeyValueDialogUtil.showInputDialog(
                activity, "Set Virtual Stick Advanced Param",
                JsonUtil.toJson(virtualStickVM.virtualStickAdvancedParam.value), "", false
            ) {
                it?.apply {
                    val param = JsonUtil.toBean(this, VirtualStickFlightControlParam::class.java)
                    if (param == null) {
                        ToastUtils.showToast("Value Parse Error")
                        return@showInputDialog
                    }
                    virtualStickVM.virtualStickAdvancedParam.postValue(param)
                }
            }
        }
        binding?.btnSendVirtualStickAdvancedParam?.setOnClickListener {
            virtualStickVM.virtualStickAdvancedParam.value?.let {
                virtualStickVM.sendVirtualStickAdvancedParam(it)
            }
        }
        binding?.btnEnableVirtualStickAdvancedMode?.setOnClickListener {
            virtualStickVM.enableVirtualStickAdvancedMode()
        }
        binding?.btnDisableVirtualStickAdvancedMode?.setOnClickListener {
            virtualStickVM.disableVirtualStickAdvancedMode()
        }
        binding?.btnEnableVirtualStick?.setOnClickListener {
            virtualStickVM.enableVirtualStick(object : CommonCallbacks.CompletionCallback {
                override fun onSuccess() {
                    ToastUtils.showToast("enableVirtualStick success.")
                }

                override fun onFailure(error: IDJIError) {
                    ToastUtils.showToast("enableVirtualStick error, $error")
                }
            })
        }
        binding?.btnDisableVirtualStick?.setOnClickListener {
            virtualStickVM.disableVirtualStick(object : CommonCallbacks.CompletionCallback {
                override fun onSuccess() {
                    ToastUtils.showToast("disableVirtualStick success.")
                }

                override fun onFailure(error: IDJIError) {
                    ToastUtils.showToast("disableVirtualStick error, $error")
                }
            })
        }
//        binding?.btnSimulateStickClick?.setOnClickListener {
//            // Call the simulateStickClick function when the button is clicked
//            simulateForwardClick(isLeftStick = true, durationMillis = 1000)
//        }

    }

    private fun initStickListener() {
        binding?.leftStickView?.setJoystickListener(object : OnScreenJoystickListener {
            override fun onTouch(joystick: OnScreenJoystick?, pX: Float, pY: Float) {
                var leftPx = 0F
                var leftPy = 0F

                if (abs(pX) >= derivation) {
                    leftPx = pX
                }

                if (abs(pY) >= derivation) {
                    leftPy = pY
                }

                virtualStickVM.setLeftPosition(
                    (leftPx * Stick.MAX_STICK_POSITION_ABS).toInt(),
                    (leftPy * Stick.MAX_STICK_POSITION_ABS).toInt()
                )

                // Send joystick data to WebSocket server
                sendMessageToServer("Joystick left: $leftPx, $leftPy")
            }
        })

        binding?.rightStickView?.setJoystickListener(object : OnScreenJoystickListener {
            override fun onTouch(joystick: OnScreenJoystick?, pX: Float, pY: Float) {
                var rightPx = 0F
                var rightPy = 0F

                if (abs(pX) >= derivation) {
                    rightPx = pX
                }

                if (abs(pY) >= derivation) {
                    rightPy = pY
                }

                virtualStickVM.setRightPosition(
                    (rightPx * Stick.MAX_STICK_POSITION_ABS).toInt(),
                    (rightPy * Stick.MAX_STICK_POSITION_ABS).toInt()
                )

                // Send joystick data to WebSocket server
                sendMessageToServer("Joystick right: $rightPx, $rightPy")
            }
        })
    }

    private fun moveRight(roll: Float) {
        virtualStickVM.setRightPosition(
            (roll * Stick.MAX_STICK_POSITION_ABS).toInt(), // Positive roll for right movement
            0 // Neutral pitch to avoid forward/backward movement
        )
//        moveDrone(roll = roll, throttle = 0f, yaw = 0f, pitch = 0f)
    }
    private fun moveLeft(roll: Float) {
        virtualStickVM.setRightPosition(
            (-roll * Stick.MAX_STICK_POSITION_ABS).toInt(), // Negative roll for left movement
            0 // Neutral pitch to avoid forward/backward movement
        )
//        moveDrone(roll = -roll, throttle = 0f, yaw = 0f, pitch = 0f)
    }
    private fun stopDrone() {
        // Reset all stick values to neutral (0)
        virtualStickVM.setLeftPosition(0, 0) // Neutral yaw and throttle
        virtualStickVM.setRightPosition(0, 0) // Neutral roll and pitch
        ToastUtils.showToast("Drone stopped.")
    }
    private fun moveDrone(roll: Float, throttle: Float, yaw: Float, pitch: Float) {
        // Set the left stick position for yaw and throttle
        virtualStickVM.setLeftPosition(
            (yaw * Stick.MAX_STICK_POSITION_ABS).toInt(),
            (throttle * Stick.MAX_STICK_POSITION_ABS).toInt()
        )

        // Set the right stick position for roll and pitch
        virtualStickVM.setRightPosition(
            (roll * Stick.MAX_STICK_POSITION_ABS).toInt(),
            (pitch * Stick.MAX_STICK_POSITION_ABS).toInt()
        )
        val location = LocationCoordinate2D()

        // Get latitude and longitude
        val latitude = location.latitude
        val longitude = location.longitude

//        ToastUtils.showToast("lat: $latitude, long: $longitude")
        // Optionally, send a WebSocket message to report the movement
//        sendMessageToServer("Drone movement: Roll=$roll, Throttle=$throttle, Yaw=$yaw, Pitch=$pitch")
    }
    private fun showHeight() {
        val takeOffHeightString = Util.getHeight(context)
//        TakeOffWidget.ModelState.TakeOff.toString()
        val height = view?.height
        ToastUtils.showToast("height: $height, $takeOffHeightString")
    }


    private fun updateVirtualStickInfo() {
        val builder = StringBuilder()
        builder.append("Speed level:").append(virtualStickVM.currentSpeedLevel.value)
        builder.append("\n")
        builder.append("Use rc stick as virtual stick:").append(virtualStickVM.useRcStick.value)
        builder.append("\n")
        builder.append("Is virtual stick enable:")
            .append(virtualStickVM.currentVirtualStickStateInfo.value?.state?.isVirtualStickEnable)
        builder.append("\n")
        builder.append("Current control permission owner:")
            .append(virtualStickVM.currentVirtualStickStateInfo.value?.state?.currentFlightControlAuthorityOwner)
        builder.append("\n")
        builder.append("Change reason:")
            .append(virtualStickVM.currentVirtualStickStateInfo.value?.reason)
        builder.append("\n")
        builder.append("Rc stick value:").append(virtualStickVM.stickValue.value?.toString())
        builder.append("\n")
        builder.append("Is virtual stick advanced mode enable:")
            .append(virtualStickVM.currentVirtualStickStateInfo.value?.state?.isVirtualStickAdvancedModeEnabled)
        builder.append("\n")
        builder.append("Virtual stick advanced mode param:")
            .append(virtualStickVM.virtualStickAdvancedParam.value?.toJson())
        val location = LocationCoordinate2D()
        builder.append("\n")
        mainHandler.post {
            binding?.virtualStickInfoTv?.text = builder.toString()
        }
    }
}