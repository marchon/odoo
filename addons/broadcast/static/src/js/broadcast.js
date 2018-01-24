
odoo.define('broadcast', function(require) {
var Widget = require('web.Widget');
var bus = require('bus.bus').bus;
var rpc = require('web.rpc');


var Broadcast = Widget.extend({
    template: 'broadcast.main',
    events: {
        'click .fa.o_audio:not(.active),.fa.o_video:not(.active)': '_onOpenMedia',
        'click .fa.o_audio.active,.fa.o_video.active': '_onCloseMedia',
    },

    mediaConfig: {
        audio: true,
        video: { width: 400, height: 300 },
        preview: false,
    },
    peerConfig: {iceServers: [
        {url: 'stun:stun.l.google.com:19302'},
        {url: 'stun:stun1.l.google.com:19302'},
        {url: 'stun:stun2.l.google.com:19302'},
        {url: 'stun:stun3.l.google.com:19302'},
        {url: 'stun:stun4.l.google.com:19302'},
        {url: 'stun:stun.services.mozilla.com'}
    ]},

    init: function (parent) {
        this.partner_id = $('.o_user_menu').text().indexOf('Admin') !== -1 ? 6 : 3;
        $(window).on('beforeunload', this.destroy.bind(this));
        return this._super(parent);
    },
    start: function () {
        var self = this;
        bus.start_polling();
        this.__onNodifications = function (notifications) {
            notifications = _.filter(notifications, function (notification) {
                return notification[0][1] === "broadcast";
            });
            var broadcasts = _.map(notifications, function (notification) {
                return JSON.parse(notification[1]);
            });
            broadcasts = _.filter(broadcasts, function (broadcast) {
                return broadcast.partner_id === self.partner_id;
            });
            var index = _.findIndex(broadcasts, {type: 'call'});
            if (index !== -1) {
                broadcasts.splice(index+1);
            }

            broadcasts.reverse();
            _.each(broadcasts, function (broadcast) {
                if (broadcast) {
                    if (broadcast.type === 'disconnect') {
                        self._onEnd();
                    } else {
                        self._onCall(broadcast);
                    }
                }
            });
        };
        bus.on('notification', this, this.__onNodifications);
    },
    destroy: function () {
        this._super();
        bus.off('notification', this, this.__onNodifications);
        this._endCall();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _endCall: function () {
        if (!this.peerConnection) {
            return;
        }

        rpc.query({
            route: '/broadcast/disconnect',
            params: {partner_id: this.partner_id}
        });

        this.localMedia = null;
        this.peerConnection.close();
        this.peerConnection = null;

        // videoCallButton.removeAttribute("disabled");
        // endCallButton.setAttribute("disabled", true);

        if (this.localVideoStream) {
            this.localVideoStream.getTracks().forEach(function (track) {
                track.stop();
            });
            this.localVideoStream = null;
        }
        if (this.localVideo) {
            this.localVideo.pause();
            this.localVideo.src = "";
            $(this.localVideo).remove();
            this.localVideo = null;
        }
        if (this.remoteVideo) {
            this.remoteVideo.pause();
            this.remoteVideo.src = "";
            $(this.remoteVideo).remove();
            this.remoteVideo = null;
        }
        this.$('.fa.o_audio.active,.fa.o_video.active').removeClass('active');
    },
    _prepareCall: function () {
        var self = this;
        if (this.peerConnection) {
            return this.peerConnection;
        }
        this.defPeerConnection = new Promise(function (resolve, reject) {
          resolve();
        });

        var pc = this.peerConnection = new RTCPeerConnection(this.peerConfig);
        pc.onicecandidate = this._onIceCandidate.bind(this);
        pc.onaddstream = this._onAddStream.bind(this);
        pc.onremovestream = function (event) {
            console.log(event.type);
        };
        pc.oniceconnectionstatechange = function (event) {
            if (self.isDestroyed()) {
                return;
            }
            switch(this.iceConnectionState) {
                case "closed":
                case "failed":
                case "disconnected": self._endCall();
            }
        };
        pc.onicegatheringstatechange = function (event) {
            console.log(event.type);
        };
        pc.onsignalingstatechange = function (event) {
            console.log(event.type);
        };
        pc.onnegotiationneeded = function (event) {
            console.log(event.type);
        };
        return pc;
    },
    _addVideo: function (stream, video) {
        if (!video) {
            video = document.createElement('video');
            $(video).appendTo(this.$('div'));
        }

        console.log(video);

        (function () {
            if ('srcObject' in video) {
                video.srcObject = stream;
            }
            if ('createObjectURL' in URL) {
                video.src = URL.createObjectURL(stream);
            }
            if ('mozSrcObject' in video) {
                video.mozSrcObject = stream;
            }
        })();
        video.autoplay = true;
        video.controls = true;
        video.play();
        return video;
    },
    _addAudio: function (stream) {
        console.log("");
        console.log(new Error().stack);
        console.log("");

        var AudioContext = window.AudioContext || window.webkitAudioContext;
        var audioContext = new AudioContext();

        // Create an AudioNode from the stream
        var mediaStreamSource = audioContext.createMediaStreamSource(stream);

        // Connect it to destination to hear yourself
        // or any other node for processing!
        mediaStreamSource.connect(audioContext.destination);

        return audioContext;
    },
    _createAndSendDescription: function (type) {
        var self = this;
        var pc = this.peerConnection;
        return (type === 'offer' ? pc.createOffer() : pc.createAnswer())
            .then(function (description) {
                var desc = new RTCSessionDescription(description);
                return pc.setLocalDescription(new RTCSessionDescription(desc))
                    .then(function () {
                        return rpc.query({
                            route: '/broadcast/call',
                            params: {
                                type: 'call',
                                partner_id: self.partner_id,
                                media: self.localMedia,
                                desc: desc
                            }
                        });
                    });
            })
            .catch(function (err) { console.error(err); });
    },
    _call: function (type, media) {
        var self = this;
        var pc = this._prepareCall();

        if (!this.mediaConfig[media]) {
            throw 'Not available';
        }
        if (this.localMedia === media) {
            return;
        }
        if (this.localMedia) {
            throw 'close current media';
        }
        this.localMedia = media;

        var mediaConfig = _.pick(this.mediaConfig, media === 'video' ? ['video', 'audio'] : ['audio']);
        navigator.mediaDevices.getUserMedia(mediaConfig)
            .then(function (stream) {
                self.localVideoStream = stream;
                if (self.mediaConfig.preview) {
                    if (media === 'video') {
                        self.localVideo = self._addVideo(stream);
                    } else {
                        self.localAudio = self._addAudio(stream);
                    }
                }
                pc.addStream(stream);
            })
            .then(this._createAndSendDescription.bind(this, type));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    // send any ice candidates to the other peer
    _onIceCandidate: function (event) {
        var self = this;
        if (!event.candidate) {
            return;
        }
        return rpc.query({
            route: '/broadcast/call',
            params: {
                partner_id: self.partner_id,
                media: self.localMedia,
                type: 'candidate',
                candidate: event.candidate
            }
        });
    },
    // once remote stream arrives, show it in the remote video element
    _onAddStream: function (evt) {
        if (this.remoteMedia === 'video') {
            this.remoteVideo = this._addVideo(evt.stream, this.remoteVideo);
        } else if (this.remoteMedia === 'audio') {
            this.remoteAudio = this._addAudio(evt.stream, this.remoteAudio);
        }
    },
    /**
     * When the offer arrives, this function is triggered, and given our "video-offer" message
     *
     * returns: {Promise}
     */
    _onCall: function (data) {
        var pc = this._prepareCall();
        this.remoteMedia = data.media;

        console.log('_onCall', this.remoteMedia, data);

        if (data.desc && data.desc.sdp) {
            console.log("Received SDP from remote peer.");
            var session = new RTCSessionDescription(data.desc);
            pc.setRemoteDescription(session);
        } else if (data.candidate) {
            console.log("Received ICECandidate from remote peer.");
            var candidate = new RTCIceCandidate(data.candidate);
            pc.addIceCandidate(candidate);
        }
    },
    _onEnd: function (data) {
        console.log("Received 'close call' signal from remote peer.");
        this._endCall();
    },
    _onOpenMedia: function (event) {
        var type = this.peerConnection ? 'answer' : 'offer';
        var media = $(event.target).addClass('active').hasClass('o_audio') ? 'audio' : 'video';
        this._call(type, media);
    },
    _onCloseMedia: function (event) {
        var media = $(event.target).addClass('active').hasClass('o_audio') ? 'audio' : 'video';
        this._endCall();
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
