var NdbProperty = function (name, ndbType, value) {
    this.Name = name;
    this.NdbType = ndbType;

    if(value)
    {
        this.Value = value;
    }
    else
    {
        this.Value = DBUtils.GetDefaultValue(propertyInfo.NdbType);
    }
};

var KeyProperty = function (name, kind, urlsafe_key) {
    NdbProperty.call(this, name, "KeyProperty", {'kind':kind, 'urlsafe_key': urlsafe_key})
};
KeyProperty.prototype = Object.create(NdbProperty.prototype);
KeyProperty.prototype.constructor = KeyProperty;

var StructuredProperty = function(name, value){
    NdbProperty.call(this, name, "StructuredProperty", value)
}

StructuredProperty.prototype = Object.create(NdbProperty.prototype);
StructuredProperty.prototype.constructor = StructuredProperty;

var PolymorphicSqlClass = function (PolyData) {
    /// <param name="fields" type='PolymorphicSqlClass'></param>

    /// <field type='String'></field>
    this.Schema = PolyData.Schema;
    /// <field type='String'></field>
    this.Table = PolyData.Table;
    /// <field value='{}'></field>
    this.Fields = {};

    for (var index = 0; index < PolyData.Fields.length; index++) {
        this.Fields[PolyData.Fields[index].Name.toUpperCase()] = PolyData.Fields[index];
    }
    
};

PolymorphicSqlClass.prototype.GetColumn = function (columnName){
    return this.Fields[columnName.toUpperCase()];
};


var RecordData = function (id, fields, poly) {
    /// <field name="Id" type='Number' integer='true'></field>
    this.Id = id;

    /// <field name="Fields" type='Array' elementType='ColumnInfo'></field>
    this.Fields = [];
    for (var fieldName in poly.Fields) {
        this.Fields.push(new ColumnInfo(poly.Fields[fieldName], fields[fieldName]));
    }
};

RecordData.prototype.Clear = function (Poly) {
    /// <summary>Resets the record data to the default for the given PolySqlClass, with an ID of -1</summary>
    /// <param name="Poly" type='PolymorphicSqlClass'></param>

    this.Id = -1;
    this.Fields = [];
    for (var fieldName in Poly.Fields) {
        this.Fields.push(new ColumnInfo(poly));
    }
};

RecordData.prototype.GetField = function (columnName) {
    /// <param name="columnName" type='String'></param>
    for (var index in this.Fields) {
        if (this.Fields[index].Name.toUpperCase() == columnName.toUpperCase()) {
            return this.Fields[index];
        }
    }
    return null;
};

RecordData.prototype.GetFieldValue = function (columnName) {
    /// <param name="columnName" type='String'></param>
    for (var index in this.Fields)
    {
        if(this.Fields[index].Name.toUpperCase() == columnName.toUpperCase())
        {
            return this.Fields[index].Value;
        }
    }
    return null;
};

RecordData.prototype.SetFieldValue = function (columnName, newValue) {
    /// <param name="columnName" type='String'></param>
    /// <param name="newValue" type='Object'></param>

    for (var index in this.Fields) {
        if (this.Fields[index].Name.toUpperCase() == columnName.toUpperCase()) {
            this.Fields[index].Value = newValue;
        }
    }
};

RecordData.prototype.GetColumnNames = function () {
    /// <returns type='Object'></returns>

    var columnNames = {}

    for (var index in this.Fields) {
        columnNames[this.Fields[index].Name.toUpperCase()] = this.Fields[index].Name.toUpperCase();
    }

    return columnNames;
}

var RecordWrapper = function (polySqlClass, recData) {
    /// <param name="polySqlClass" type="PolymorphicSqlClass"></param>
    /// <param name="recData" type="RecordData"></param>

    /// <field name="Poly" type='PolymorphicSqlClass'></field>
    this.Poly = polySqlClass;
    /// <field name="Data" type='RecordData'></field>
    this.Data = recData;
};

RecordWrapper.prototype.Compare = function (otherRecord, includeWoWEditLock, FuzzyPrecision) {
    /// <param name="otherRecord" type="RecordWrapper"></param>
    /// <param name="includeWoWEditLock" type="Boolean">Determines if the WoWEditLockColumns should be compared as well</param>
    /// <param name="FuzzyPrecision" type="Boolean">Determines if the EXACT or MOSTLY EXACT percision should be used for float numbers</param>
    /// <returns type='Number' integer='true'>0 if equal, non-zero if unqual</returns>

    if(this.Poly.Table !== otherRecord.Poly.Table){
        return -1;
    }
    for (var fieldKey in this.Data.GetColumnNames())
    {
        if(this.Data.GetFieldValue(fieldKey) !== otherRecord.Data.GetFieldValue(fieldKey))
        {
            return -1;
        }
    }

    return 0;
}

RecordWrapper.prototype.GetChangedColumns = function (otherRecord, includeWoWEditLock, FuzzyPrecision) {
    /// <param name="otherRecord" type="RecordWrapper"></param>
    /// <param name="includeWoWEditLock" type="Boolean">Determines if the WoWEditLockColumns should be compared as well</param>
    /// <param name="FuzzyPrecision" type="Boolean">Determines if the EXACT or MOSTLY EXACT percision should be used for float numbers</param>

    /// <field name="changedColumns" type='Array' elementType='ColumnInfo'></field>
    var changedColumns = []

    for (var fieldKey in this.Data.GetColumnNames()) {
        if (this.Data.GetFieldValue(fieldKey) !== otherRecord.Data.GetFieldValue(fieldKey)) {
            changedColumns.push(new ColumnInfo(this.Poly.GetColumn(fieldKey), this.Data.GetField(fieldKey)));
        }
    }
    return changedColumns;
};