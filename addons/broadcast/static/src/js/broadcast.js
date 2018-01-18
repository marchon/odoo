
odoo.define('broadcast', function(require) {
var Widget = require('web.Widget');
var bus = require('bus.bus').bus;
var rpc = require('web.rpc');


var Broadcast = Widget.extend({
    template: 'broadcast.main',

    mediaConfig: {
        audio: true,
        video: { width: 400, height: 300 },
        preview: true,
    },
    peerConfig: {'iceServers': 
        [{'url': 'stun:stun.services.mozilla.com'}, 
         {'url': 'stun:stun.l.google.com:19302'}]
    },

    init: function (parent) {
        this._super(parent);
        this.isCaller = true;
    },
    start: function () {
        bus.start_polling();
        bus.on('broadcast.desc', this, function(r){ console.log(r); });
        this.run();
    },
    run: function () {
        this._startPeerConnection();
        this._startMedia();
    },
    // run start(true) to initiate a call
    _startPeerConnection: function () {
        this.peerConnection = new RTCPeerConnection(_.pick(this.peerConfig, ['audio', 'video']));
        this.peerConnection.onicecandidate = this._onPeerConnectionCandidate.bind(this);
        this.peerConnection.ontrack = this._onPeerConnectionTrack.bind(this);
    },
    _startMedia: function () {
        var self = this;
        // get the local stream, show it in the local video element and send it
        navigator.mediaDevices.getUserMedia(this.mediaConfig)
            .then(function (stream) {
                if (self.mediaConfig.preview) {
                    if (self.mediaConfig.video) {
                        self._onAddVideo(stream);
                    } else {
                        self._onAddAudio(stream);
                    }
                }
                if (self.peerConnection) {
                    self._onMediaStreamBrodcast(stream);
                }
            })
            .catch(function (err) { console.error(err); });
    },
    _onAddVideo: function (stream) {
        var video = document.createElement('video');
        video.autoplay = true;
        $(video).appendTo(this.$el);

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
            self._sendPeerDescription(desc);
        }
    },
    _sendPeerDescription: function (desc) {
        //console.log('>>>>>', desc);

        
        rpc.query({
            route: '/longpolling/send',
            params: {channel: 'broadcast.desc', message: JSON.stringify(desc)}
        });

        // var self = this;
        // return rpc.query({
        //     route: '/broadcast/sendPeerDescription',
        //     params: {desc: desc}
        // }).then(function(result){
        //     console.log(result);
        // });
        //signalingChannel.send(JSON.stringify({ "sdp": desc }));
    },

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
    _onVideoOfferMsg: function (evt) {
        if (!this.peerConnection) {
            this.isCaller = false;
            this._startPeerConnection();
        }
        var signal = JSON.parse(evt.data);
        if (signal.sdp) {
            var desc = new RTCSessionDescription(msg.sdp);
            myPeerConnection.setRemoteDescription(desc);
        }
        else {
            this.peerConnection.addIceCandidate(new RTCIceCandidate(signal.candidate));
        }
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
