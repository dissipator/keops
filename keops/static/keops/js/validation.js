
keops.submit = function (form, url) {
    form.submit({
        clientValidation: true,
        url: url,
        success: function () {
            console.log('success');
        },
        failure: function (form, action) {
            switch (action.failureType) {
            case Ext.form.action.Action.CLIENT_INVALID:
                Ext.Msg.alert('Erro', 'Favor preencher os campos corretamente.');
                break;
            }
        }
    });
};
