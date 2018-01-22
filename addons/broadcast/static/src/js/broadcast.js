
odoo.define('broadcast', function(require) {
var Widget = require('web.Widget');
var bus = require('bus.bus').bus;
var rpc = require('web.rpc');


var Broadcast = Widget.extend({
    template: 'broadcast.main',
    events: {
        'click .o_audio,.o_video': '_onSendCall',
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

    init: function (parent) {
        this.partner_id = $('.o_user_menu').text().indexOf('Admin') !== -1 ? 6 : 3;
        $(window).on('beforeunload', this.destroy.bind(this));
        return this._super(parent);
    },
    start: function () {
        var self = this;
        bus.start_polling();
        this.__onNodifications = function (notifications) {
            _.each(notifications, function (notification) {
                if (notification[0][1] === "broadcast.call") {
                    var data = JSON.parse(notification[1]);
                    if (data.type === 'call') {
                        self.type = 'answer';
                        self._onReceiveCall(data.sdp);
                    } else if (data.partner_id === self.partner_id) {
                        self._onDisconnectCall();
                    }
                }
            });
        };
        bus.on('notification', this, this.__onNodifications);
    },
    destroy: function () {
        this._super();
        bus.off('notification', this, this.__onNodifications);
        if (!this.peerConnection) {
            return;
        }
        if (this.media === 'video') {
            var video = this.$('video')[0];
            if (video && video.srcObject) {
                video.srcObject.getTracks().forEach(function (track) {
                    track.stop();
                });
                video.srcObject = null;
            }
        }
        this.peerConnection.close();
        rpc.query({
            route: '/broadcast/disconnect',
            params: {partner_id: self.partner_id}
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _startPeerConnection: function () {
        var self = this;
        if (this.peerConnection) {
            return;
        }
        this.defPeerConnection = new Promise(function (resolve, reject) {
          resolve();
        });

        this.peerConnection = new RTCPeerConnection(this.peerConfig);
        this.peerConnection.onicecandidate = this._onPeerConnectionCandidate.bind(this);
        this.peerConnection.onaddstream = this._onPeerConnectionStream.bind(this);
        this.peerConnection.onremovestream = function (event) {
            console.log(event.type, event);
        };
        this.peerConnection.oniceconnectionstatechange = function (event) {
            if (self.isDestroyed()) {
                return;
            }
            switch(this.iceConnectionState) {
                case "closed":
                case "failed":
                case "disconnected": self.destroy();
                break;
            }
        };
        this.peerConnection.onicegatheringstatechange = function (event) {
            console.log(event.type, event);
        };
        this.peerConnection.onsignalingstatechange = function (event) {
            console.log(event.type, event);
        };
        this.peerConnection.onnegotiationneeded = function (event) {
            console.log(event.type, event);
        };
    },
    _onAddMedia: function (media, stream) {
        console.log('_onAddMedia', stream);
        if (media === 'video') {
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
        }

        // audio only

        var AudioContext = window.AudioContext || window.webkitAudioContext;
        var audioContext = new AudioContext();

        // Create an AudioNode from the stream
        var mediaStreamSource = audioContext.createMediaStreamSource(stream);

        // Connect it to destination to hear yourself
        // or any other node for processing!
        mediaStreamSource.connect(audioContext.destination);
    },
    _shareMedia: function (media) {
        var self = this;
        var pc = self.peerConnection;
        var mediaConfig = _.pick(this.mediaConfig, media === 'video' ? ['video', 'audio'] : ['audio']);

        navigator.mediaDevices.getUserMedia(mediaConfig)
            .then(function (stream) {
                if (self.mediaConfig.preview) {
                    self._onAddMedia(media, stream);
                }
                pc.addStream(stream);
            })
            .then(function (desc) {
                if (self.type === 'offer') {
                    return pc.createOffer();
                } else {
                    return pc.createAnswer();
                }
            })
            .then(function (desc) {
                return pc.setLocalDescription(desc);
            })
            .then(function () {
                return rpc.query({
                    route: '/broadcast/call',
                    params: {
                        partner_id: self.partner_id,
                        sdp: pc.localDescription
                    }
                });
            })
            .catch(function (err) { console.error(err); });
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
    _onPeerConnectionStream: function (evt) {
        var media = evt.target.remoteDescription.sdp.indexOf('video') === -1 ? 'audio' : 'video';
        this._onAddMedia(media, evt.stream);
    },

    /**
     * When the offer arrives, this function is triggered, and given our "video-offer" message
     *
     * returns: {Promise}
     */
    _onReceiveCall: function (desc) {
        this._startPeerConnection();
        if (desc.type === "offer") {
            var description = new RTCSessionDescription(desc);
            this.defPeerConnection = this.peerConnection.setRemoteDescription(description);

        } else {
            var candidate = new RTCIceCandidate(desc);
            this.defPeerConnection = this.peerConnection.addIceCandidate(candidate);
        }
    },
    _onSendCall: function (event) {
        var self = this;
        var media = $(event.target).hasClass('o_audio') ? 'audio' : 'video';

        if (!this.type) {
            this.type = 'offer';
        }
        if (!self.mediaConfig[media]) {
            throw 'Not available';
        }
        // if (this.media === media) {
        //     return;
        // }
        // if (this.media) {
        //     throw 'close current media';
        // }
        this.media = media;
        this._startPeerConnection();
        this.defPeerConnection.then(function () {
            self._shareMedia(media);
        });
    },
    _onDisconnectCall: function () {
        this.destroy();
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
