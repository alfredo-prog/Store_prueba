/**
 * jQuery plugin for creating formsets
 */
(function($) {
    $.fn.formset = function(opts) {
        var options = $.extend({}, $.fn.formset.defaults, opts);
        var $this = $(this);
        
        var $formset = $this;
        var $managementForm = $formset.find('input[name*="TOTAL_FORMS"], input[name*="INITIAL_FORMS"], input[name*="MAX_NUM_FORMS"], input[name*="MIN_NUM_FORMS"]').first().parent();
        
        var totalForms = parseInt($managementForm.find('input[name*="TOTAL_FORMS"]').val());
        var template = $formset.children().first().clone();
        
        // Update form attributes in template
        template.find(':input').each(function() {
            var name = $(this).attr('name');
            if (name) {
                $(this).attr('name', name.replace(/-\d+-/, '-__prefix__-'));
            }
            var id = $(this).attr('id');
            if (id) {
                $(this).attr('id', id.replace(/-\d+-/, '-__prefix__-'));
            }
        });
        
        template.find('label').each(function() {
            var forAttr = $(this).attr('for');
            if (forAttr) {
                $(this).attr('for', forAttr.replace(/-\d+-/, '-__prefix__-'));
            }
        });
        
        // Add form
        function addForm() {
            var newForm = template.clone();
            newForm.find(':input').each(function() {
                var name = $(this).attr('name');
                if (name) {
                    $(this).attr('name', name.replace(/__prefix__/, totalForms));
                }
                var id = $(this).attr('id');
                if (id) {
                    $(this).attr('id', id.replace(/__prefix__/, totalForms));
                }
                $(this).val('');
            });
            
            newForm.find('label').each(function() {
                var forAttr = $(this).attr('for');
                if (forAttr) {
                    $(this).attr('for', forAttr.replace(/__prefix__/, totalForms));
                }
            });
            
            // Update subtotal ID
            newForm.find('[id^="subtotal-"]').attr('id', 'subtotal-' + totalForms);
            
            totalForms++;
            $managementForm.find('input[name*="TOTAL_FORMS"]').val(totalForms);
            
            $formset.append(newForm);
            
            if (options.added) {
                options.added(newForm);
            }
        }
        
        // Add button
        var addButton = $('<button type="button">' + options.addText + '</button>')
            .addClass(options.addCssClass)
            .click(addForm);
        
        $formset.after(addButton);
        
        // Handle delete
        $formset.on('click', '[name*="DELETE"]', function() {
            var $row = $(this).closest('.formset-row');
            if ($(this).is(':checked')) {
                $row.hide();
            } else {
                $row.show();
            }
        });
        
        return this;
    };
    
    $.fn.formset.defaults = {
        prefix: 'form',
        addText: 'Add another',
        deleteText: 'Remove',
        addCssClass: 'add-row',
        deleteCssClass: 'delete-row',
        formCssClass: 'dynamic-form'
    };
})(jQuery);
