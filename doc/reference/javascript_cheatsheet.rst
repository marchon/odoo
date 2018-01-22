:banner: banners/javascript.jpg

=====================
Javascript Cheatsheet
=====================

Main classes
============

The two main classes of the odoo JS framework are

- ``Class`` (defined in ``web.Class``):
    this is an implementation of the classical OOP notion of a class.  This is
    mostly what one can expect from a class system. It has a limited support for
    multiple inheritance, via mixins.
- ``Widget`` (defined in ``web.Widget``):
    this is the basic building block for a component in the interface.  This is
    the code that represent a region of the screen, and has some support for
    binding events, triggering events, rendering templates, ...

Creating subclasses: extend/include
===================================

There are two main mechanisms to modify code in Odoo: creating a subclass (with
``extend``), and modifying in place a widget (with ``include``), also known as
monkey-patching.

- extending a class/widget
    This is the usual way to proceed:

    .. code-block:: javascript

        var SubWidget = Widget.extend({
            init: function (parent, data) {
                this._super(parent);
                this.data = data;
            },
        });

    This creates a sub widget, which allows you to instantiate then, independently
    from the parent class.  This is the classical inheritance mechanism.

- including a class/widget
    Using the ``include`` function, this modifies a class in place:

    .. code-block:: javascript

        HomeMenu.include({
            someMethod: function () {
                this._super();
                // do something else here
            }
        });

    This is obviously a dangerous operation.  There may be other incompatible
    monkey-patches in other addons.  Also, if the init method is included, then
    the code will only apply to widgets created after the monkeypatching.  In
    any case, this should be avoided in most situations.



Communication between widgets
=============================

There are many ways to communicate between components.

- From a parent to its child:
    this is a simple case. The parent widget can simply call a method on its
    child:

    .. code-block:: javascript

        this.someWidget.update(someInfo);

- From a widget to its parent/some ancestor:
    in this case, the widget's job is simply to notify its environment that
    something happened.  Since we do not want the widget to have a reference to
    its parent (this would couple the widget with its parent's implementation),
    the best way to proceed is usually to trigger an event, which will bubble up
    the component tree, by using the ``trigger_up`` method:

    .. code-block:: javascript

        this.trigger_up('open_record', { record: record, id: id});

    This event will be triggered on the widget, then will bubble up and be
    eventually caught by some upstream widget:

    .. code-block:: javascript

        var SomeAncestor = Widget.extend({
            custom_events: {
                'open_record': '_onOpenRecord',
            },
            _onOpenRecord: function (event) {
                var record = event.data.record;
                var id = event.data.id;
                // do something with the event.
            },
        });

Customizing Odoo with JavaScript
================================

First of all, remember that the first rule of customizing odoo with JS is:
*try to do it in python*.  This may seem strange, but the python framework is
quite extensible, and many behaviours can be done simply with a touch of xml or
python.  This has usually a lower cost of maintenance than working with JS.

Creating a new field widget
---------------------------

This is probably a really common usecase: we want to display some information in
a form view in a really specific (maybe business dependent) way.  For example,
assume that we want to change the text color depending on some business condition.

This can be done in three steps: creating a new widget, registering it in the
field registry, then adding the widget to the field in the form view

- creating a new widget:
    This can be done by extending a widget:

    .. code-block:: javascript

        var FieldChar = require('web.basic_fields').FieldChar;

        var CustomFieldChar = Fieldchar.extend({
            renderReadonly: function () {
                // implement some custom logic here
            },
        });

- registering it in the field registry:
    The web client needs to know the mapping between a widget name and its
    actual class.  This is done by a registry:

    .. code-block:: javascript

        var fieldRegistry = require('web.field_registry');

        fieldRegistry.add('my-custom-field', CustomFieldChar);

- adding the widget in the form view
    Note that field widgets works in form, list and kanban views:

    .. code-block:: xml

        <field name="somefield" widget="my-custom-field"/>

Modifying an existing field widget
----------------------------------

Another use case is that we want to modify an existing field widget.  For
example, the voip addon in odoo need to modify the FieldPhone widget to add the
possibility to easily call the given number on voip. This is done by *including*
the FieldPhone widget, so there is no need to change any existing form view.

Field Widgets are like every other widgets, so they can be monkey patched. This
looks like this:

.. code-block:: javascript

    var basic_fields = require('web.basic_fields');
    var Phone = basic_fields.FieldPhone;

    Phone.include({
        events: _.extend({}, Phone.prototype.events, {
            'click': '_onClick',
        }),

        _onClick: function (e) {
            if (this.mode === 'readonly') {
                e.preventDefault();
                var phoneNumber = this.value;
                // call the number on voip...
            }
        },
    });

Note that there is no need to add the widget to the registry, since it is already
registered.

Modifying a main widget from the interface
------------------------------------------

Another common usecase is the need to customize some elements from the user
interface.  For example, adding a message in the home menu.  The usual process
in this case is again to *include* the widget.  This is the only way to do it,
since there are no registries for those widgets.

This is usually done with code looking like this:

.. code-block:: javascript

    var AppSwitcher = require('web_enterprise.AppSwitcher');

    AppSwitcher.include({
        render: function () {
            this._super();
            // do something else here...
        },
    });


Adding a client action
----------------------

A client action is a widget which will control the part of the screen below the
menu bar.  It can have a control panel, if necessary.  Creating a client action
can be done in two steps: implementing a new widget, and registering the widget
in the action registry.

- Implementing a new client action:
    This is done by creating a widget:

    .. code-block:: javascript

        var ControlPanelMixin = require('web.ControlPanelMixin');
        var Widget = require('web.Widget');

        var ClientAction = Widget.extend(ControlPanelMixin, {
            ...
        });

    Do not add the controlpanel mixin if you do not need it.  Note that some
    code is needed to interact with the control panel (via the
    ``update_control_panel`` method given by the mixin).

- Registering the client action:
    As usual, we need to make the web client aware of the mapping between
    client actions and the actual class:

    .. code-block:: javascript

        var core = require('web.core');

        core.action_registry.add('my-custom-action', ClientAction);


Then, to use the client action in the web client, we need to create a client
action record (a record of the model ``ir.actions.client``) with the proper
``tag`` attribute:

    .. code-block:: xml

        <record id="my_client_action" model="ir.actions.client">
            <field name="name">Some Name</field>
            <field name="tag">my-custom-action</field>
        </record>

Creating a new view (from scratch)
----------------------------------

Creating a new view is a more advanced topic.  This cheatsheet will only
highlight the steps that will probably need to be done (in no particular order):

- adding a new view type to the field ``type`` of ``ir.ui.view``::

    class View(models.Model):
        _inherit = 'ir.ui.view'

        type = fields.Selection(selection_add=[('map', "Map")])

- adding the new view type to the field ``view_mode`` of ``ir.actions.act_window.view``::

    class ActWindowView(models.Model):
        _inherit = 'ir.actions.act_window.view'

        view_mode = fields.Selection(selection_add=[('map', "Map")])


- creating the four main pieces which makes a view (in JavaScript):
    we need a view (a subclass of ``AbstractView``, this is the factory), a
    renderer (from ``AbstractRenderer``), a controller (from ``AbstractController``)
    and a model (from ``AbstractModel``).  I suggest starting by simply
    extending the superclasses:

    .. code-block:: javascript

        var AbstractController = require('web.AbstractController');
        var AbstractModel = require('web.AbstractModel');
        var AbstractRenderer = require('web.AbstractRenderer');
        var AbstractView = require('web.AbstractView');

        var MapController = AbstractController.extend({});
        var MapRenderer = AbstractRenderer.extend({});
        var MapModel = AbstractModel.extend({});

        var MapView = AbstractView.extend({
            config: {
                Model: MapModel,
                Controller: MapController,
                Renderer: MapRenderer,
            },
        });

- adding the view to the registry:
    As usual, the mapping between a view type and the actual class needs to be
    updated:

    .. code-block:: javascript

        var viewRegistry = require('web.view_registry');

        viewRegistry.add('map', MapView);

- implementing the four main classes:
    The ``View`` class needs to parse the ``arch`` field and setup the other
    three classes.  The ``Renderer`` is in charge of representing the data in
    the user interface, the ``Model`` is supposed to talk to the server, to
    load data and process it.  And the ``Controller`` is there to coordinate,
    to talk to the web client, ...

- creating some views in the database:

    .. code-block:: xml

        <record id="customer_map_view" model="ir.ui.view">
            <field name="name">customer.map.view</field>
            <field name="model">res.partner</field>
            <field name="arch" type="xml">
                <map latitude="partner_latitude" longitude="partner_longitude">
                    <field name="name"/>
                </map>
            </field>
        </record>


Customizing an existing view
------------------------------

Assume we need to create a custom version of a generic view.  For example, a
kanban view with some extra *ribbon-like* widget on top (to display some
specific custom information). In that case, this can be done with 3 steps:
extend the kanban view (which also probably mean extending controllers/renderers
and/or models), then registering the view in the view registry, and finally,
using the view in the kanban arch (a specific example is the helpdesk dashboard).

- extending a view:
    Here is what it could look like:

    .. code-block:: javascript

        var HelpdeskDashboardRenderer = KanbanRenderer.extend({
            ...
        });

        var HelpdeskDashboardModel = KanbanModel.extend({
            ...
        });

        var HelpdeskDashboardController = KanbanController.extend({
            ...
        });

        var HelpdeskDashboardView = KanbanView.extend({
            config: _.extend({}, KanbanView.prototype.config, {
                Model: HelpdeskDashboardModel,
                Renderer: HelpdeskDashboardRenderer,
                Controller: HelpdeskDashboardController,
            }),
        });

- adding it to the view registry:
    as usual, we need to inform the web client of the mapping between the name
    of the views and the actual class.

    .. code-block:: javascript

        var viewRegistry = require('web.view_registry');
        viewRegistry.add('helpdesk_dashboard', HelpdeskDashboardView);

- using it in an actual view:
    we now need to inform the web client that a specific ``ir.ui.view`` needs to
    use our new class.  Note that this is a web client specific concern.  From
    the point of view of the server, we still have a kanban view.  The proper
    way to do this is by using a special attribute ``js_class`` (which will be
    renamed someday into ``widget``, because this is really not a good name) on
    the root node of the arch:

    .. code-block:: xml

        <record id="helpdesk_team_view_kanban" model="ir.ui.view" >
            ...
            <field name="arch" type="xml">
                <kanban js_class="helpdesk_dashboard">
                    ...
                </kanban>
            </field>
        </record>
