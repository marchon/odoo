
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
        preview: true,
    },
    peerConfig: {iceServers: [
        {url: 'stun:stun.l.google.com:19302'},
        {url: 'stun:stun1.l.google.com:19302'},
        {url: 'stun:stun2.l.google.com:19302'},
        {url: 'stun:stun3.l.google.com:19302'},
        {url: 'stun:stun4.l.google.com:19302'},
        {url: 'stun:stun.services.mozilla.com'}
    ]},

    init: function (parent, partner_id) {
        this.partner_id = partner_id;
        $(window).on('beforeunload', this.destroy.bind(this));
        this.local = {};
        this.remote = {};
        this.localStream = new MediaStream();
        this.remoteStream = new MediaStream();
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

    _endCall: function (type, media) {
        if (!this.peerConnection) {
            return;
        }

        if (type !== 'remote') {
            this._endLocalCall();
        }
        if (type !== 'local') {
            this._endRemoteCall();
        }

        if (!_.isEmpty(this.remote) || !_.isEmpty(this.local)) {
            return;
        }

        this.peerConnection.close();
        this.peerConnection = null;
    },
    _endLocalCall: function () {
        var self = this;
        rpc.query({
            route: '/broadcast/disconnect',
            params: {partner_id: this.partner_id}
        });

        this.localStream.getTracks().forEach(function (track) {
            track.stop();
            self.localStream.removeTrack(track);
        });

        var video = this.remote.video;
        if (video && video !== true) {
            video.pause();
            video.src = "";
            $(video).remove();
        }
        delete this.local.video;

        this.$('.fa.o_audio.active,.fa.o_video.active').removeClass('active');
    },
    _endRemoteCall: function () {
        var self = this;
        this.remoteStream.getTracks().forEach(function (track) {
            track.stop();
            self.remoteStream.removeTrack(track);
        });

        var video = this.remote.video;
        if (video && video !== true) {
            video.pause();
            video.src = "";
            $(video).remove();
        }
        delete this.remote.video;
    },
    _prepareCall: function (kill) {
        var self = this;
        if (this.peerConnection) {
            if (kill) {
                this.peerConnection.close();
                this.peerConnection = null;
            } else {
                return this.peerConnection;
            }
        }

        var pc = this.peerConnection = new RTCPeerConnection(this.peerConfig);

        pc.addStream(this.localStream);

        pc.onicecandidate = this._onIceCandidate.bind(this);
        pc.onaddstream = this._onAddStream.bind(this);
        pc.onremovestream = function (event) {
            console.log(event.type);
        };
        pc.oniceconnectionstatechange = function (event) {
            console.log(event);
            if (self.isDestroyed()) {
                return;
            }
            switch(this.iceConnectionState) {
                case "closed":
                case "failed":
                case "disconnected": self._endCall('remote');
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
        if (!video || video === true) {
            video = document.createElement('video');
            $(video).appendTo(this.$('div'));
        }

        (function () {
            if ('srcObject' in video) {
                try {
                    video.srcObject = stream;
                } catch(e) {}
            }
            if ('mozSrcObject' in video) {
                try {
                   video.mozSrcObject = stream;
                } catch(e) {}
            }
            if ('createObjectURL' in URL) {
                video.src = URL.createObjectURL(stream);
            }
        })();
        video.autoplay = true;
        video.play();
        return video;
    },
    _addAudio: function (stream, audio) {
        if (!audio || audio === true) {
            audio = document.createElement('video');
        }

        (function () {
            if ('srcObject' in audio) {
                try {
                    audio.srcObject = stream;
                } catch(e) {}
            }
            if ('mozSrcObject' in audio) {
                try {
                   audio.mozSrcObject = stream;
                } catch(e) {}
            }
            if ('createObjectURL' in URL) {
                audio.src = URL.createObjectURL(stream);
            }
        })();
        audio.autoplay = true;
        audio.play();
        return audio;
    },
    _createAndSendDescription: function (type) {
        var self = this;
        var pc = this.peerConnection;
        return (type === 'offer' ? pc.createOffer() : pc.createAnswer(pc.remoteDescription))
            .then(function (description) {
                return pc.setLocalDescription(new RTCSessionDescription(description))
                    .then(function () {
                        return rpc.query({
                            route: '/broadcast/call',
                            params: {
                                type: 'call',
                                partner_id: self.partner_id,
                                desc: description
                            }
                        });
                    });
            })
            .catch(function (err) {
                console.error(err);
                self._endCall();
            });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    // send any ice candidates to the other peer
    _onIceCandidate: function (event) {
        var self = this;

        console.log('_onIceCandidate', event);

        if (!event.candidate) {
            return;
        }
        return rpc.query({
            route: '/broadcast/call',
            params: {
                partner_id: self.partner_id,
                type: 'candidate',
                candidate: event.candidate
            }
        });
    },
    // once remote stream arrives, show it in the remote video element
    _onAddStream: function (evt) {
        var self = this;
        var tracks = evt.stream.getTracks();
        tracks.forEach(function(track) {
            self.remoteStream.addTrack(track);
        });
        var medias = _.pluck(tracks, 'kind');

        console.log('_onAddStream', medias);

        if (medias.indexOf('video') !== -1) {
            if (this.remote.audio) {
                this.remote.audio.stop();
            }
            this.remote.video = this._addVideo(evt.stream, this.remote.video);
        } else if (medias.indexOf('audio') !== -1) {
            this.remote.audio = this._addAudio(evt.stream, this.remote.audio);
        }
    },
    /**
     * When the offer arrives, this function is triggered, and given our "video-offer" message
     *
     * returns: {Promise}
     */
    _onCall: function (data) {
        var self = this;
        var pc = this._prepareCall(data.desc && data.desc.type === 'offer');

        if (data.desc && data.desc.sdp) {
            console.log("Received SDP from remote peer.");
            var session = new RTCSessionDescription(data.desc);
            var promise = pc.setRemoteDescription(session);
            if (data.desc.type === 'offer') {
                promise.then(this._createAndSendDescription.bind(this, 'answer'));
            }
        } else if (data.candidate) {
            console.log("Received ICECandidate from remote peer.");
            var candidate = new RTCIceCandidate(data.candidate);
            pc.addIceCandidate(candidate);
        }
    },
    _onEnd: function (data) {
        console.log("Received 'close call' signal from remote peer.");
        this._endCall('remote');
    },
    _onOpenMedia: function (event) {
        var self = this;
        var pc = this._prepareCall(true);

        var media = $(event.target).addClass('active').hasClass('o_audio') ? 'audio' : 'video';

        this.local[media] = true;

        var mediaConfig = _.pick(this.mediaConfig, media === 'video' ? ['video', 'audio'] : ['audio']);
        var promise = navigator.mediaDevices.getUserMedia(mediaConfig);
        promise.then(function (stream) {
                if (self.mediaConfig.preview) {
                    if (media === 'video') {
                        self.local.video = self._addVideo(stream);
                    } else {
                        self.local.audio = self._addAudio(stream);
                    }
                }
                stream.getTracks().forEach(function(track) {
                    self.localStream.addTrack(track);
                });
            });

        promise.then(this._createAndSendDescription.bind(this, 'offer'));
    },
    _onCloseMedia: function (event) {
        var media = $(event.target).addClass('active').hasClass('o_audio') ? 'audio' : 'video';
        this._endCall('local', media);
    },
});

(function autoAdd() {
    if ($('.o_home_menu').size()) {
        if ($('.o_user_menu').text().indexOf('aaa') !== -1)
        {
        new Broadcast(this, 3).prependTo($('.o_home_menu'));
        new Broadcast(this, 6).prependTo($('.o_home_menu'));

        } else {
            new Broadcast(this, $('.o_user_menu').text().indexOf('Admin') !== -1 ? 6 : 3).prependTo($('.o_home_menu'));
            new Broadcast(this, 45).prependTo($('.o_home_menu'));
        }
    } else {
        setTimeout(autoAdd, 500);
    }
})();

});
