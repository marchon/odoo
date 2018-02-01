odoo.define('Broadcast', function(require) {

var bus = require('bus.bus').bus;
var Class = require('web.Class');
var mixins = require('web.mixins');
var rpc = require('web.rpc');

var TIMEOUT_OFFER = 5000;

var Broadcast = Class.extend(mixins.EventDispatcherMixin, {
    init: function (parent, partnerID, mediaConfig, peerConfig) {
        mixins.EventDispatcherMixin.init.call(this);
        this.setParent(parent);

        this.localStream = new MediaStream();
        this.remoteStream = new MediaStream();

        this.partnerID = partnerID;
        this.peerConfig = peerConfig;
    },

    destroy: function () {
        rpc.query({
            route: '/broadcast/disconnect',
            params: {
                partner_id: this.partnerID
            }
        });

        this._closeCall();

        this.trigger_up('call_disconnected');
        mixins.EventDispatcherMixin.destroy.call(this);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    createOffer: function (mediaConfig) {
        if (this.peerConnection) {
            this._closeCall();
        }
        this.mediaConfig = mediaConfig;
        this._openCall();
        this._makeOffer(this.type || 'offer');
    },
    /**
     * When the offer arrives, this function is triggered, and given our "video-offer" message
     */
    receiveOffer: function (data) {
        var self = this;

        clearTimeout(this._makeOfferTimeout);

        if (data.desc && data.desc.type === 'offer') {
            this._closeCall();

            if (data.mediaConfig) {
                this.mediaConfig = this.mediaConfig || {};
                if (this.mediaConfig.audio === undefined && data.mediaConfig.audio) {
                    this.mediaConfig.audio = true;
                }
                if (this.mediaConfig.video === undefined && data.mediaConfig.video) {
                    this.mediaConfig.video = data.mediaConfig.video;
                }
                if (data.mediaConfig.remoteScreen) { // can ask to receive screen sharing
                    this.mediaConfig.screen = true;
                }
            }
        }

        if (!this.peerConnection) {
            this._openCall();
        }

        if (data.desc && data.desc.sdp) {
            console.log("Received SDP from remote peer.");
            var session = new RTCSessionDescription(data.desc);
            var promise = this.peerConnection.setRemoteDescription(session);
            if (data.desc.type === 'offer') {
                promise.then(this._makeOffer.bind(this, 'answer'));
            }
        } else if (data.candidate) {
            console.log("Received ICECandidate from remote peer.");
            var candidate = new RTCIceCandidate(data.candidate);
            this.peerConnection.addIceCandidate(candidate);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _closeCall: function () {
        var self = this;
        this.localStream.getTracks().forEach(function (track) {
            track.stop();
            self.localStream.removeTrack(track);
        });
        this.remoteStream.getTracks().forEach(function (track) {
            track.stop();
            self.remoteStream.removeTrack(track);
        });
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
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
                                partner_id: self.partnerID,
                                desc: description,
                                mediaConfig: self.mediaConfig,
                            }
                        });
                    });
            })
            .catch(function (err) {
                console.error(err);
                self.destroy();
            });
    },
    _makeOffer: function (type) {
        var self = this;
        this.type = type;
        var mediaConfig = this.mediaConfig;
        var promise = navigator.mediaDevices.getUserMedia(mediaConfig);
        promise.then(function (stream) {
            if (mediaConfig.video) {
                self.trigger_up('local_video', {stream: stream});
            } else if (mediaConfig.audio) {
                self.trigger_up('local_audio', {stream: stream});
            }
            stream.getTracks().forEach(function(track) {
                self.localStream.addTrack(track);
            });
        });
        promise.then(function () {
            clearTimeout(self._makeOfferTimeout);
            if (type === 'offer') {
                self._makeOfferTimeout = setTimeout(self.destroy.bind(self), TIMEOUT_OFFER);
            }
            if (self.peerConnection) { // if the connection is already open
                self._createAndSendDescription(self.type);
            }
        });
    },
    _openCall: function () {
        this.peerConnection = new RTCPeerConnection(this.peerConfig);
        this.peerConnection.addStream(this.localStream);
        this.peerConnection.onicecandidate = this._onIceCandidate.bind(this);
        this.peerConnection.onaddstream = this._onAddStream.bind(this);
        this.peerConnection.oniceconnectionstatechange = this._onIceConnectionStateChange.bind(this);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    // once remote stream arrives, show it in the remote video element
    _onAddStream: function (event) {
        var self = this;
        var tracks = event.stream.getTracks();
        tracks.forEach(function(track) {
            self.remoteStream.addTrack(track);
        });
        var medias = _.pluck(tracks, 'kind');

        if (medias.indexOf('video') !== -1) {
            this.trigger_up('remote_video', {stream: event.stream});
        } else if (medias.indexOf('audio') !== -1) {
            this.trigger_up('remote_audio', {stream: event.stream});
        }
    },
    // send any ice candidates to the other peer
    _onIceCandidate: function (event) {
        if (!event.candidate) {
            return;
        }
        return rpc.query({
            route: '/broadcast/call',
            params: {
                partner_id: this.partnerID,
                type: 'candidate',
                candidate: event.candidate
            }
        });
    },
    _onIceConnectionStateChange: function (event) {
        if (this.isDestroyed()) {
            return;
        }
        switch(this.peerConnection.iceConnectionState) {
            case "closed":
            case "failed":
            case "disconnected": this.destroy();
        }
    },
});

var BroadcastCollector = Class.extend(mixins.EventDispatcherMixin, {
    custom_events: {
        local_video: '_onStream',
        local_audio: '_onStream',
        local_screen: '_onStream',
        remote_video: '_onStream',
        remote_audio: '_onStream',
        remote_screen: '_onStream',
        call_disconnected: '_onDisconnect',
    },

    mediaConfig: {
        audio: true,
        video: {
            small: {width: 256, height: 192 },
            medium: {width: 512, height: 384 },
            big: {width: 1024, height: 768 },
        }
    },
    peerConfig: {iceServers: [
        {url: 'stun:stun.l.google.com:19302'},
        {url: 'stun:stun1.l.google.com:19302'},
        {url: 'stun:stun2.l.google.com:19302'},
        {url: 'stun:stun3.l.google.com:19302'},
        {url: 'stun:stun4.l.google.com:19302'},
        {url: 'stun:stun.services.mozilla.com'}
    ]},

    init: function () {
        mixins.EventDispatcherMixin.init.call(this);
        this.broadcasts = {};
        $(window).on('beforeunload', this.destroy.bind(this));
        
        bus.start_polling();
        this.__onNodifications = this._onNodifications.bind(this);
        bus.on('notification', this, this.__onNodifications);
    },

    destroy: function () {
        bus.off('notification', this, this.__onNodifications);
        mixins.EventDispatcherMixin.destroy.call(this);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Open a new rtc call and begin to stream.
     *
     * @param {Integer} partnerID
     * @param {Object} [mediaConfig] use default value if not set
     * @param {false|'small'|'medium'|'big'} [mediaConfig.video] medium size by default
     * @param {Boolean} [mediaConfig.audio] true by default (and true when video is enable)
     * @returns {Deferred}
     */
    openCall: function (partnerID, mediaConfig) {
        if (!mediaConfig.audio && !mediaConfig.video && !mediaConfig.screen) {
            this.closeCall(partnerID);
            return;
        }

        if (!this.broadcasts[partnerID]) {
            this.broadcasts[partnerID] = new Broadcast(this, partnerID, this.peerConfig);
        }
        this.broadcasts[partnerID].createOffer(this._config(mediaConfig));
    },
    closeCall: function (partnerID) {
        var broadcast = this.broadcasts[partnerID];
        if (broadcast) {
            this.broadcasts[partnerID].destroy();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * A partner rtc calls was destroyed
     *
     * @private
     * @param {odooEvent} event
     */
    _onDisconnect: function (event) {
        event.stopPropagation();
        var partnerID = event.target.partnerID;
        var broadcast = this.broadcasts[partnerID];
        if (!broadcast) {
            return;
        }
        delete this.broadcasts[partnerID];
        this.trigger('disconnect', {partnerID: partnerID});
    },
    /**
     * 
     *
     * @private
     */
    _onStream: function (event) {
        event.stopPropagation();
        this.trigger(_.str.camelize(event.name), {
            partnerID: event.target.partnerID,
            data: event.data.stream,
        });
    },
    /**
     * 
     *
     * @private
     */
    _onNodifications: function (notifications) {
        var self = this;
        var data = {};
        _.each(notifications, function (notification) {
            if (notification[0][1] === "broadcast") {
                var broadcast = JSON.parse(notification[1]);
                if (!data[broadcast.partnerID]) {
                    data[broadcast.partnerID] = [];
                }
                data[broadcast.partnerID].push(broadcast);
            }
        });

        _.each(data, function (broadcasts) {
            var index = _.findIndex(broadcasts, {type: 'call'});
            if (index !== -1) {
                broadcasts.splice(index+1);
            }
            if (!broadcasts.length) {
                return;
            }
            broadcasts.reverse();

            _.each(broadcasts, function (bc) {
                var partnerID = bc.partner_id;
                var broadcast = self.broadcasts[partnerID];
                if (bc.type === 'disconnect') {
                    if (broadcast) {
                        console.log("Received 'close call' signal from remote peer.");
                        broadcast.destroy();
                    }
                } else {
                    if (!broadcast) {
                        // in the event that a communication is received without this
                        // being provided, the configuration will be identical to that
                        // of the incoming offer.
                        // (eg: press F5 just after responding to a communication request)
                        broadcast = new Broadcast(self, partnerID, self.peerConfig);
                        self.broadcasts[partnerID] = broadcast;
                    }
                    broadcast.receiveOffer(bc);
                }
            });
        });
    },
    /**
     * 
     *
     * @private
     * @param {Object} mediaConfig
     * @param {false|'small'|'medium'|'big'} [mediaConfig.video] medium size by default
     * @param {Boolean} [mediaConfig.audio] true by default (and true when video is enable)
     * @returns {Object}
     */
    _config: function (mediaConfig) {
        mediaConfig = mediaConfig || {video: 'medium'};
        var config = {};
        if(mediaConfig.video !== false) {
            config.audio = true;
            config.video = this.mediaConfig.video[mediaConfig.video] || this.mediaConfig.video.medium;
        } else if (mediaConfig.audio !== false) {
            config.audio = true;
        }
        return config;
    },
});


var broadcastCollector = new BroadcastCollector();

return {
    closeCall: broadcastCollector.closeCall.bind(broadcastCollector),
    openCall: broadcastCollector.openCall.bind(broadcastCollector),
    on: function (events, dest, func) {
        return broadcastCollector.on(events, dest, function (data) {
            if (data.partnerID === dest.partnerID) {
                func.call(dest, data.data);
            }
        });
    },
    off: function () {
        return broadcastCollector.off.apply(broadcastCollector, arguments);
    }
};

});


odoo.define('broadcast.widget', function(require) {

var Broadcast = require('Broadcast');
var Widget = require('web.Widget');


function srcStream (media, stream) {
    media.autoplay = true;
    if ('createObjectURL' in URL) {
        try {
            media.src = URL.createObjectURL(stream);
            media.play();
            return;
        } catch (e) {}
    }
    if ('srcObject' in media) {
        media.srcObject = stream;
    } else if ('mozSrcObject' in media) {
        media.mozSrcObject = stream;
    }
    media.play();
}


var BroadcastWidget = Widget.extend({
    template: 'broadcast.widget',

    events: {
        'click .fa.o_audio': '_onClickAudio',
        'click .fa.o_video': '_onClickVideo',
        'click .fa.o_screen': '_onClickScreen',
    },

    init: function (parent, partnerID) {
        this.audio = false;
        this.video = false;
        this.screen = false;
        this.partnerID = partnerID;
        return this._super(parent);
    },

    start: function () {
        Broadcast.on('localVideo', this, this._onLocalVideoStream);
        Broadcast.on('localAudio', this, this._onLocalAudioStream);
        Broadcast.on('localScreen', this, this._onLocalScreenStream);
        Broadcast.on('remoteVideo', this, this._onRemoteVideoStream);
        Broadcast.on('remoteAudio', this, this._onRemoteAudioStream);
        Broadcast.on('remoteScreen', this, this._onRemoteScreenStream);
        Broadcast.on('disconnect', this, this._onDisconnect);

        this._super();
    },

    destroy: function () {
        Broadcast.off('localVideo', this, this._onLocalVideoStream);
        Broadcast.off('localAudio', this, this._onLocalAudioStream);
        Broadcast.off('localScreen', this, this._onLocalScreenStream);
        Broadcast.off('remoteVideo', this, this._onRemoteVideoStream);
        Broadcast.off('remoteAudio', this, this._onRemoteAudioStream);
        Broadcast.off('remoteScreen', this, this._onRemoteScreenStream);

        Broadcast.closeCall(this.partnerID);

        Broadcast.off('disconnect', this, this._onDisconnect);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     *
     * @private
     * @param {mouseEvent} event
     */
    _onClickAudio: function (event) {
        this.audio = !this.audio;
        this.$('.fa.o_audio').toggleClass('active', this.audio);
        Broadcast.openCall(this.partnerID, {
            audio: this.audio,
            video: this.video,
            screen: this.screen,
        });
    },
    /**
     *
     * @private
     * @param {mouseEvent} event
     */
    _onClickVideo: function (event) {
        this.video = !this.video;
        if (this.video && !this.audio) {
            this.audio = true;
        }
        this.$('.fa.o_audio').toggleClass('active', this.audio);
        this.$('.fa.o_video').toggleClass('active', this.video);
        Broadcast.openCall(this.partnerID, {
            audio: this.audio,
            video: this.video,
            screen: this.screen,
        });
    },
    /**
     *
     * @private
     * @param {mouseEvent} event
     */
    _onClickScreen: function (event) {
        this.screen = !this.screen;
        this.$('.fa.o_screen').toggleClass('active', this.screen);
        Broadcast.openCall(this.partnerID, {
            audio: this.audio,
            video: this.video,
            screen: this.screen,
        });
    },
    /**
     *
     * @private
     */
    _onDisconnect: function () {
        this.audio = false;
        this.video = false;
        this.screen = false;
        this.$('.fa').removeClass('active');
        this.$('video, audio')
            .addClass('hidden')
            .each(function () {
                this.pause();
                this.src = "";
            });
    },
    /**
     *
     * @private
     * @param {Stream} stream
     */
    _onLocalVideoStream: function (stream) {
        if (!this.video) {
            this.audio = true;
            this.video = true;
            this.$('.fa.o_audio').toggleClass('active', this.audio);
            this.$('.fa.o_video').toggleClass('active', this.video);
        }
        return;
        var $video = this.$('.o_local_video').removeClass('hidden');
        srcStream($video[0], stream);
    },
    /**
     *
     * @private
     * @param {Stream} stream
     */
    _onLocalAudioStream: function (stream) {
        if (!this.video) {
            this.audio = true;
            this.$('.fa.o_audio').toggleClass('active', this.audio);
        }
        return;
        var $audio = this.$('.o_local_audio').removeClass('hidden');
        srcStream($audio[0], stream);
    },
    /**
     *
     * @private
     * @param {Stream} stream
     */
    _onLocalScreenStream: function (stream) {},
    /**
     *
     * @private
     * @param {odooEvent} event
     */
    _onRemoteVideoStream: function (stream) {
        var $video = this.$('.o_remote_video').removeClass('hidden');
        srcStream($video[0], stream);
    },
    /**
     *
     * @private
     * @param {Stream} stream
     */
    _onRemoteAudioStream: function (stream) {
        var $audio = this.$('.o_remote_audio').removeClass('hidden');
        srcStream($audio[0], stream);
    },
    /**
     *
     * @private
     * @param {Stream} stream
     */
    _onRemoteScreenStream: function (stream) {
        var $video = this.$('.o_remote_screen').removeClass('hidden');
        srcStream($video[0], stream);
    },

});

(function autoAdd() {
    if ($('.o_home_menu').size()) {
        if ($('body').html().indexOf('chm') !== -1) {
            new BroadcastWidget(this, 3).prependTo($('.o_home_menu'));
            new BroadcastWidget(this, 6).prependTo($('.o_home_menu'));

        } else if ($('body').html().indexOf('Demo User') !== -1)  {
            new BroadcastWidget(this, 3).prependTo($('.o_home_menu'));
            new BroadcastWidget(this, 45).prependTo($('.o_home_menu'));
        } else {
            new BroadcastWidget(this, 6).prependTo($('.o_home_menu'));
            new BroadcastWidget(this, 45).prependTo($('.o_home_menu'));
        }
    } else {
        setTimeout(autoAdd, 500);
    }
})();

});
