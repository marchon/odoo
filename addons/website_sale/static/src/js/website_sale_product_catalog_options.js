odoo.define('website_sale.product_catalog_options', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var options = require('web_editor.snippets.options');
var productCatalog = require('website_sale.product_catalog');
var rpc = require('web.rpc');

var _t = core._t;
var QWeb = core.qweb;

options.registry.product_catalog = options.Class.extend({
    xmlDependencies: ['/website_sale/static/src/xml/website_sale_product_catalog.xml'],
    /**
     * @override
     */
    start: function () {
        this.productCatalogData = _.pick(this.$target.data(), 'catalog_type', 'product_selection', 'product_ids', 'sortby', 'x', 'y', 'category_id');
        this._setGrid();
        this._bindGridEvents();
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Select catalog type.
     *
     * @see this.selectClass for parameters
     */
    catalogType: function (previewMode, value) {
        this.productCatalogData.catalog_type = value;
        this._renderProducts();
    },
    /**
     * Set Grid size.
     */
    gridSize: function () {
        this._setGrid();
        this._renderProducts();
    },
    /**
     * Sort products.
     *
     * @see this.selectClass for parameters
     */
    sortby: function (previewMode, value) {
        this.productCatalogData.sortby = value;
        this._renderProducts();
    },
    /**
     * Products selection.
     *
     * @see this.selectClass for parameters
     */
    productSelection: function (previewMode, value, $li) {
        switch (value) {
            case 'all':
                this.productCatalogData.product_selection = value;
                this._renderProducts();
                break;
            case 'category':
                this._categorySelection();
                break;
            case 'manual':
                this._manualSelection();
                break;
        }

    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * Bind events of grid option.
     *
     * @private
     */
    _bindGridEvents: function () {
        this.$el.on('mouseenter', 'ul[name="size"] table', function (event) {
            $(event.currentTarget).addClass('oe_hover');
        });
        this.$el.on('mouseleave', 'ul[name="size"] table', function (event) {
            $(event.currentTarget).removeClass('oe_hover');
        });
        this.$el.on('mouseover', 'ul[name="size"] td', function (event) {
            var $td = $(event.currentTarget);
            var $table = $td.closest('table');
            var x = $td.index() + 1;
            var y = $td.parent().index() + 1;

            var tr = [];
            for (var yi = 0; yi < y; yi++) {
                tr.push('tr:eq(' + yi + ')');
            }
            var $select_tr = $table.find(tr.join(','));
            var td = [];
            for (var xi = 0; xi < x; xi++) {
                td.push('td:eq(' + xi + ')');
            }
            var $selectTd = $select_tr.find(td.join(','));
            $table.find('td').removeClass('select');
            $selectTd.addClass('select');
        });
    },
    /**
     * Select products category wise.
     *
     * @private
     */
    _categorySelection: function () {
        var self = this;
        rpc.query({
            model: 'product.public.category',
            method: 'search_read',
            fields: ['id', 'name'],
        }).then(function (result) {
            var dialog = new Dialog(null, {
                title: _t('Select Product Category'),
                $content: $(QWeb.render('website_sale.categorySelection')),
                buttons: [
                    {text: _t('Save'), classes: 'btn-primary', close: true, click: function () {
                        var categoryid = dialog.$content.find('[name="selection"]').val();
                        self.productCatalogData.category_id = categoryid;
                        self.productCatalogData.product_selection = 'category';
                        self.$el.find('li[data-product-selection]').removeClass('active')
                            .filter('li[data-product-selection="category"]').addClass('active');
                        self._renderProducts();
                    }},
                    {text: _t('Discard'), close: true}
                ]
            });
            dialog.$content.find('[name="selection"]').val(self.productCatalogData.category_id);
            dialog.$content.find('[name="selection"]').select2({
                width: '70%',
                data: _.map(result, function (r) {
                    return {'id': r.id, 'text': r.name};
                }),
            });
            dialog.$content.find('[name="selection"]').change(function () {
                rpc.query({
                    model: 'product.template',
                    method: 'search_count',
                    args:[[['public_categ_ids', 'child_of', [parseInt($(this).val())]], ['website_published', '=', true]]]
                }).then(function (result) {
                    dialog.$('.alert-info').toggleClass('hidden', result !== 0);
                    dialog.$footer.find('.btn-primary').prop('disabled', result === 0);
                });
            });
            dialog.open();
        });
    },
    /**
     * Get product ids.
     *
     * @private
     * @returns {Array} Contains product ids.
     */
    _getProductIds: function () {
        return _.map(this.$target.find('.o_product_item'), function (el) {
            return $(el).data('product-id');
        });
    },
    /**
     * Select products manually.
     *
     * @private
     */
    _manualSelection: function () {
        var self = this;
        rpc.query({
            model: 'product.template',
            method: 'search_read',
            fields: ['id', 'name'],
            domain: [['website_published', '=', true]]
        }).then(function (result) {
            var dialog = new Dialog(null, {
                title: _t('Select Product Manually'),
                $content: $(QWeb.render('website_sale.manualSelection')),
                buttons: [
                    {text: _t('Save'), classes: 'btn-primary', close: true, click: function () {
                        self.productCatalogData.product_ids = dialog.$content.find('[name="selection"]').val();
                        self.productCatalogData.product_selection = 'manual';
                        self.productCatalogData.sortby = '';
                        self.$el.find('li[data-product-selection]').removeClass('active')
                            .filter('li[data-product-selection="manual"]').addClass('active');
                        self._renderProducts();
                    }},
                    {text: _t('Discard'), close: true}
                ]
            });
            dialog.$content.find('[name="selection"]').val(self._getProductIds());
            dialog.$content.find('[name="selection"]').select2({
                width: '100%',
                multiple: true,
                maximumSelectionSize: self.productCatalogData.catalog_type === 'grid' ? self.productCatalogData.x * self.productCatalogData.y : 16,
                data: _.map(result, function (r) {
                    return {'id': r.id, 'text': r.name};
                }),
            }).change(function () {
                dialog.$footer.find('.btn-primary').prop('disabled', dialog.$content.find('[name="selection"]').val() === "");
            });
            dialog.$content.find('[name="selection"]').select2("container").find("ul.select2-choices").sortable({
                containment: 'parent',
                start: function() {dialog.$content.find('[name="selection"]').select2("onSortStart"); },
                update: function() {dialog.$content.find('[name="selection"]').select2("onSortEnd"); }
            });
            dialog.open();
        });
    },
    /**
     * @override
     */
    _setActive: function () {
        this._super.apply(this, arguments);
        var mode = this.productCatalogData.catalog_type;
        this.$el.find('li[data-product-selection]').removeClass('active')
            .filter('li[data-product-selection=' + this.productCatalogData.product_selection + ']').addClass('active');
        this.$el.find('[data-grid-size]:first').parent().parent().toggle(mode === 'grid');
        this.$el.find('li[data-catalog-type]').removeClass('active')
            .filter('li[data-catalog-type=' + this.productCatalogData.catalog_type + ']').addClass('active');
        this.$el.find('[data-sortby]:first').parent().parent().toggle(this.productCatalogData.product_selection !== 'manual');
        if (this.productCatalogData.product_selection !== 'manual') {
            this.$el.find('li[data-sortby]').removeClass('active')
            .filter('li[data-sortby=' + this.productCatalogData.sortby + ']').addClass('active');
        }
    },

    /**
     * Set selected size on grid option.
     *
     * @private
     */
    _setGrid: function () {
        var $td = this.$el.find('.select:last');
        if ($td.length) {
            this.productCatalogData.x = $td.index() + 1;
            this.productCatalogData.y = $td.parent().index() + 1;
        }
        var x = this.productCatalogData.x;
        var y = this.productCatalogData.y;
        var $grid = this.$el.find('ul[name="size"]');
        var $selected = $grid.find('tr:eq(0) td:lt(' + x + ')');
        if (y >= 2) {
            $selected = $selected.add($grid.find('tr:eq(1) td:lt(' + x + ')'));
        }
        if (y >= 3) {
            $selected = $selected.add($grid.find('tr:eq(2) td:lt(' + x + ')'));
        }
        if (y >= 4) {
            $selected = $selected.add($grid.find('tr:eq(3) td:lt(' + x + ')'));
        }
        $grid.find('td').removeClass('selected');
        $selected.addClass('selected');
    },
    /**
     * Render products by initialize 'productCatalog' widget.
     *
     * @private
     */
    _renderProducts: function () {
        var self = this;
        _.each(this.productCatalogData, function (value, key) {
            self.$target.attr('data-' + key, value);
            self.$target.data(key, value);
        });
        // Disable sortby when manual selection
        this.$el.find('[data-sortby]:first').parent().parent().toggle(this.productCatalogData.product_selection !== 'manual');
        this.trigger_up('animation_start_demand', {
            editableMode: true,
            $target: self.$target,
        });
    },
});
});
