{#
    Copyright (C) 2026 YORI Project
    All rights reserved.

    YORI Policy Library - Pre-built templates
#}

<script>
    $(document).ready(function() {
        loadLibrary();
    });

    function loadLibrary() {
        $.ajax({
            url: '/api/yori/policy/library',
            method: 'GET',
            success: function(response) {
                if (response.result === 'success') {
                    renderLibrary(response.templates);
                } else {
                    showAlert('danger', 'Failed to load library');
                }
            }
        });
    }

    function renderLibrary(templates) {
        var container = $('#libraryContainer');
        container.empty();

        // Group by category
        var categories = {};
        templates.forEach(function(t) {
            var cat = t.category || 'Other';
            if (!categories[cat]) categories[cat] = [];
            categories[cat].push(t);
        });

        // Render each category
        Object.keys(categories).sort().forEach(function(category) {
            var section = $('<div class="panel panel-default">' +
                '<div class="panel-heading"><h4 class="panel-title">' + escapeHtml(category) + '</h4></div>' +
                '<div class="panel-body"><div class="row"></div></div></div>');

            var row = section.find('.row');
            categories[category].forEach(function(template) {
                var card = '<div class="col-md-4" style="margin-bottom: 15px;">' +
                    '<div class="panel panel-info">' +
                        '<div class="panel-heading">' +
                            '<h5 class="panel-title">' + escapeHtml(template.title) + '</h5>' +
                        '</div>' +
                        '<div class="panel-body">' +
                            '<p>' + escapeHtml(template.description) + '</p>' +
                            '<button class="btn btn-primary btn-sm" onclick="installPolicy(\'' + escapeHtml(template.name) + '\')">' +
                                '<i class="fa fa-download"></i> Install' +
                            '</button>' +
                            ' <button class="btn btn-default btn-sm" onclick="previewPolicy(\'' + escapeHtml(template.name) + '\')">' +
                                '<i class="fa fa-eye"></i> Preview' +
                            '</button>' +
                        '</div>' +
                    '</div>' +
                '</div>';
                row.append(card);
            });

            container.append(section);
        });
    }

    function installPolicy(name) {
        $.ajax({
            url: '/api/yori/policy/install/' + encodeURIComponent(name),
            method: 'POST',
            success: function(response) {
                if (response.result === 'success') {
                    showAlert('success', 'Policy "' + name + '" installed successfully');
                } else {
                    showAlert('danger', 'Install failed: ' + (response.message || 'Unknown error'));
                }
            }
        });
    }

    function previewPolicy(name) {
        // Redirect to editor with template loaded
        window.location.href = '/ui/yori/policyEditor/' + encodeURIComponent(name);
    }

    function showAlert(type, message) {
        var alert = '<div class="alert alert-' + type + ' alert-dismissible" role="alert">' +
            '<button type="button" class="close" data-dismiss="alert"><span>&times;</span></button>' +
            message + '</div>';
        $('#alertArea').html(alert);

        if (type === 'success') {
            setTimeout(function() {
                $('#alertArea .alert').fadeOut();
            }, 3000);
        }
    }

    function escapeHtml(text) {
        if (!text) return '';
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }
</script>

<div class="content-box">
    <div id="alertArea"></div>

    <div class="content-box-header">
        <h3><i class="fa fa-book"></i> Policy Library</h3>
    </div>

    <div class="content-box-main">
        <p class="text-muted">
            Pre-built policy templates for common use cases. Click "Install" to add a policy to your system,
            or "Preview" to view and customize before installing.
        </p>

        <div class="row" style="margin-bottom: 15px;">
            <div class="col-md-12">
                <a href="/ui/yori/policies" class="btn btn-default">
                    <i class="fa fa-arrow-left"></i> Back to Policies
                </a>
                <a href="/ui/yori/policyEditor" class="btn btn-primary">
                    <i class="fa fa-plus"></i> Create Custom Policy
                </a>
            </div>
        </div>

        <div id="libraryContainer">
            <div class="text-center text-muted" style="padding: 50px;">
                <i class="fa fa-spinner fa-spin fa-2x"></i>
                <p>Loading policy library...</p>
            </div>
        </div>
    </div>
</div>
