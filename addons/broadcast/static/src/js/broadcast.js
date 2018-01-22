
odoo.define('broadcast', function(require) {
var Widget = require('web.Widget');
var bus = require('bus.bus').bus;
var rpc = require('web.rpc');


var Broadcast = Widget.extend({
    template: 'broadcast.main',
    events: {
        'click h3': '_onSendCall',
    },

    mediaConfig: {
        audio: true,
        video: { width: 400, height: 300 },
        preview: true,
    },
    peerConfig: {'iceServers': 
        [{'url': 'stun:stun.services.mozilla.com'}, 
         {'url': 'stun:stun.l.google.com:19302'}]
    },

    start: function () {
        var self = this;
        bus.start_polling();
        this.__onNodifications = function (notifications) {
            _.each(notifications, function (notification) {
                if (notification[0][1] === "broadcast.call") {
                    self._onReceiveCall(JSON.parse(notification[1]));
                }
            });
        };
        bus.on('notification', this, this.__onNodifications);
    },
    destroy: function () {
        this._super();
        bus.off('notification', this, this.__onNodifications);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _onAddVideo: function (stream) {
        var video = document.createElement('video');
        video.autoplay = true;
        $(video).appendTo(this.$('.o_video'));

        if ('srcObject' in video) {
            return (video.srcObject = stream);
        } else if ('mozSrcObject' in video) {
            return (video.mozSrcObject = stream);
        } else if ('createObjectURL' in URL) {
            try {
                // deprecated
                return (video.src = URL.createObjectURL(stream));
            } catch (e) {}
        }
        console.error('createObjectURL/srcObject both are not supported.');
    },
    _onAddAudio: function (stream) {
        var AudioContext = window.AudioContext || window.webkitAudioContext;
        var audioContext = new AudioContext();

        // Create an AudioNode from the stream
        var mediaStreamSource = audioContext.createMediaStreamSource(stream);

        // Connect it to destination to hear yourself
        // or any other node for processing!
        mediaStreamSource.connect(audioContext.destination);
    },
    // send video
    _onMediaStreamBrodcast: function (stream) {
        var self = this;
        var pc = this.peerConnection;

        pc.addStream(stream);

        if (this.isCaller) {
            pc.createOffer()
                .then(gotDescription)
                .catch(function (err) { console.error(err); });
        } else {
            pc.createAnswer()
                .then(gotDescription)
                .catch(function (err) { console.error(err); });
        }

        function gotDescription(desc) {
            pc.setLocalDescription(desc);
            rpc.query({
                route: '/broadcast/call',
                params: {partner_id: 6, sdp: JSON.stringify(desc)}
            });
        }
    },
    _startPeerConnection: function () {
        this.peerConnection = new RTCPeerConnection(this.peerConfig);
        this.peerConnection.onicecandidate = this._onPeerConnectionCandidate.bind(this);
        this.peerConnection.ontrack = this._onPeerConnectionTrack.bind(this);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    // send any ice candidates to the other peer
    _onPeerConnectionCandidate: function (evt) {
        //console.log(evt.candidate);
        //signalingChannel.send(JSON.stringify({ "candidate": evt.candidate }));
    },
    // once remote stream arrives, show it in the remote video element
    _onPeerConnectionTrack: function (evt) {
        console.warn(evt.stream);
        //this._onAddVideo(evt.stream);
    },

    /**
     * When the offer arrives, this function is triggered, and given our "video-offer" message
     *
     * returns: {Promise}
     */
    _onReceiveCall: function (sdp) {
        var self = this;
        var def;

        console.log('_onReceiveCall', sdp);

        if (sdp.type === "offer") {
            this._startPeerConnection();
            var description = new RTCSessionDescription(sdp);
            def = this.peerConnection.setRemoteDescription(description);
        } else {
            var candidate = new RTCIceCandidate(signal.candidate);
            def = this.peerConnection.addIceCandidate(candidate);
        }

        def.then(function () {
            return navigator.mediaDevices.getUserMedia(self.mediaConfig);
        }).then(function(stream) {
            self._onAddVideo(stream);
            return self.peerConnection.addStream(stream);
        });
    },
    _onSendCall: function () {
        var self = this;
        this.isCaller = true;
        this._startPeerConnection();
        // get the local stream, show it in the local video element and send it

        navigator.mediaDevices.getUserMedia(this.mediaConfig).then(function (stream) {
            if (self.mediaConfig.preview) {
                if (self.mediaConfig.video) {
                    //self._onAddVideo(stream);
                } else {
                    self._onAddAudio(stream);
                }
            }
            if (self.peerConnection) {
                self._onMediaStreamBrodcast(stream);
            }
        });
    },
});

(function autoAdd() {
    if ($('.o_home_menu').size()) {
        new Broadcast().prependTo($('.o_home_menu'));
    } else {
        setTimeout(autoAdd, 500);
    }
})();

});
