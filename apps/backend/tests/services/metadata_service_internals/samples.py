SAMPLE_19115_3_NO_REVISION = b"""\
<mdb:MD_Metadata xmlns:mdb="http://standards.iso.org/iso/19115/-3/mdb/2.0"
                 xmlns:cit="http://standards.iso.org/iso/19115/-3/cit/2.0"
                 xmlns:gco="http://standards.iso.org/iso/19115/-3/gco/1.0"
                 xmlns:mri="http://standards.iso.org/iso/19115/-3/mri/1.0">
  <mdb:dateInfo>
    <cit:CI_Date>
      <cit:date><gco:DateTime>2024-01-01T00:00:00</gco:DateTime></cit:date>
      <cit:dateType>
        <cit:CI_DateTypeCode codeList="x" codeListValue="creation"/>
      </cit:dateType>
    </cit:CI_Date>
  </mdb:dateInfo>
  <mdb:identificationInfo>
    <mri:MD_DataIdentification>
      <mri:citation>
        <cit:CI_Citation>
          <cit:date>
            <cit:CI_Date>
              <cit:date><gco:Date>2024-01-01</gco:Date></cit:date>
              <cit:dateType>
                <cit:CI_DateTypeCode codeList="x" codeListValue="creation"/>
              </cit:dateType>
            </cit:CI_Date>
          </cit:date>
        </cit:CI_Citation>
      </mri:citation>
    </mri:MD_DataIdentification>
  </mdb:identificationInfo>
</mdb:MD_Metadata>
"""

SAMPLE_19115_3_WITH_REVISION = b"""\
<mdb:MD_Metadata xmlns:mdb="http://standards.iso.org/iso/19115/-3/mdb/2.0"
                 xmlns:cit="http://standards.iso.org/iso/19115/-3/cit/2.0"
                 xmlns:gco="http://standards.iso.org/iso/19115/-3/gco/1.0"
                 xmlns:mri="http://standards.iso.org/iso/19115/-3/mri/1.0">
  <mdb:dateInfo>
    <cit:CI_Date>
      <cit:date><gco:DateTime>2024-01-01T00:00:00</gco:DateTime></cit:date>
      <cit:dateType>
        <cit:CI_DateTypeCode codeList="x" codeListValue="creation"/>
      </cit:dateType>
    </cit:CI_Date>
  </mdb:dateInfo>
  <mdb:dateInfo>
    <cit:CI_Date>
      <cit:date><gco:DateTime>2024-06-01T10:00:00</gco:DateTime></cit:date>
      <cit:dateType>
        <cit:CI_DateTypeCode codeList="x" codeListValue="revision"/>
      </cit:dateType>
    </cit:CI_Date>
  </mdb:dateInfo>
  <mdb:identificationInfo>
    <mri:MD_DataIdentification>
      <mri:citation>
        <cit:CI_Citation>
          <cit:date>
            <cit:CI_Date>
              <cit:date><gco:Date>2024-01-01</gco:Date></cit:date>
              <cit:dateType>
                <cit:CI_DateTypeCode codeList="x" codeListValue="creation"/>
              </cit:dateType>
            </cit:CI_Date>
          </cit:date>
          <cit:date>
            <cit:CI_Date>
              <cit:date><gco:Date>2024-06-01</gco:Date></cit:date>
              <cit:dateType>
                <cit:CI_DateTypeCode codeList="x" codeListValue="revision"/>
              </cit:dateType>
            </cit:CI_Date>
          </cit:date>
        </cit:CI_Citation>
      </mri:citation>
    </mri:MD_DataIdentification>
  </mdb:identificationInfo>
</mdb:MD_Metadata>
"""

SAMPLE_19139_NO_REVISION = b"""\
<gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                 xmlns:gco="http://www.isotc211.org/2005/gco">
  <gmd:identificationInfo>
    <gmd:MD_DataIdentification>
      <gmd:citation>
        <gmd:CI_Citation>
          <gmd:date>
            <gmd:CI_Date>
              <gmd:date><gco:Date>2024-01-01</gco:Date></gmd:date>
              <gmd:dateType>
                <gmd:CI_DateTypeCode codeList="x" codeListValue="creation"/>
              </gmd:dateType>
            </gmd:CI_Date>
          </gmd:date>
        </gmd:CI_Citation>
      </gmd:citation>
    </gmd:MD_DataIdentification>
  </gmd:identificationInfo>
</gmd:MD_Metadata>
"""

SAMPLE_19139_WITH_REVISION = b"""\
<gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                 xmlns:gco="http://www.isotc211.org/2005/gco">
  <gmd:identificationInfo>
    <gmd:MD_DataIdentification>
      <gmd:citation>
        <gmd:CI_Citation>
          <gmd:date>
            <gmd:CI_Date>
              <gmd:date><gco:Date>2024-01-01</gco:Date></gmd:date>
              <gmd:dateType>
                <gmd:CI_DateTypeCode codeList="x" codeListValue="creation"/>
              </gmd:dateType>
            </gmd:CI_Date>
          </gmd:date>
          <gmd:date>
            <gmd:CI_Date>
              <gmd:date><gco:Date>2024-06-01</gco:Date></gmd:date>
              <gmd:dateType>
                <gmd:CI_DateTypeCode codeList="x" codeListValue="revision"/>
              </gmd:dateType>
            </gmd:CI_Date>
          </gmd:date>
        </gmd:CI_Citation>
      </gmd:citation>
    </gmd:MD_DataIdentification>
  </gmd:identificationInfo>
</gmd:MD_Metadata>
"""

SAMPLE_19115_3_WITH_REVISION_DATETIME = b"""\
<mdb:MD_Metadata xmlns:mdb="http://standards.iso.org/iso/19115/-3/mdb/2.0"
                 xmlns:cit="http://standards.iso.org/iso/19115/-3/cit/2.0"
                 xmlns:gco="http://standards.iso.org/iso/19115/-3/gco/1.0"
                 xmlns:mri="http://standards.iso.org/iso/19115/-3/mri/1.0">
  <mdb:identificationInfo>
    <mri:MD_DataIdentification>
      <mri:citation>
        <cit:CI_Citation>
          <cit:date>
            <cit:CI_Date>
              <cit:date><gco:DateTime>2024-06-01T10:00:00</gco:DateTime></cit:date>
              <cit:dateType>
                <cit:CI_DateTypeCode codeList="x" codeListValue="revision"/>
              </cit:dateType>
            </cit:CI_Date>
          </cit:date>
        </cit:CI_Citation>
      </mri:citation>
    </mri:MD_DataIdentification>
  </mdb:identificationInfo>
</mdb:MD_Metadata>
"""

SAMPLE_19139_WITH_REVISION_DATETIME = b"""\
<gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                 xmlns:gco="http://www.isotc211.org/2005/gco">
  <gmd:identificationInfo>
    <gmd:MD_DataIdentification>
      <gmd:citation>
        <gmd:CI_Citation>
          <gmd:date>
            <gmd:CI_Date>
              <gmd:date><gco:DateTime>2024-06-01T10:00:00</gco:DateTime></gmd:date>
              <gmd:dateType>
                <gmd:CI_DateTypeCode codeList="x" codeListValue="revision"/>
              </gmd:dateType>
            </gmd:CI_Date>
          </gmd:date>
        </gmd:CI_Citation>
      </gmd:citation>
    </gmd:MD_DataIdentification>
  </gmd:identificationInfo>
</gmd:MD_Metadata>
"""

SAMPLE_19115_3_WITH_ONLINE_RESOURCES = b"""\
<mdb:MD_Metadata xmlns:mdb="http://standards.iso.org/iso/19115/-3/mdb/2.0"
                 xmlns:cit="http://standards.iso.org/iso/19115/-3/cit/2.0"
                 xmlns:srv="http://standards.iso.org/iso/19115/-3/srv/2.0"
                 xmlns:mrd="http://standards.iso.org/iso/19115/-3/mrd/1.0"
                 xmlns:gco="http://standards.iso.org/iso/19115/-3/gco/1.0">
    <mdb:distributionInfo>
        <mrd:MD_Distribution>
            <mrd:transferOptions>
                <mrd:MD_DigitalTransferOptions>
                    <mrd:onLine>
                        <cit:CI_OnlineResource>
                            <cit:linkage>
                                <gco:CharacterString>http://localhost:8080/geoserver/ogc/features/v1/collections/psc:proj_3948?f=json</gco:CharacterString>
                            </cit:linkage>
                            <cit:protocol>
                                <gco:CharacterString>OGC API Features</gco:CharacterString>
                            </cit:protocol>
                            <cit:name>
                                <gco:CharacterString>psc:proj_3948</gco:CharacterString>
                            </cit:name>
                            <cit:description>
                                <gco:CharacterString>proj_3948</gco:CharacterString>
                            </cit:description>
                            <cit:function>
                                <cit:CI_OnLineFunctionCode codeList="http://standards.iso.org/iso/19115/resources/Codelists/cat/codelists.xml#CI_OnLineFunctionCode" codeListValue="download" />
                            </cit:function>
                        </cit:CI_OnlineResource>
                    </mrd:onLine>
                    <mrd:onLine>
                        <cit:CI_OnlineResource>
                            <cit:linkage>
                                <gco:CharacterString>http://localhost:8080/geoserver/psc/wms</gco:CharacterString>
                            </cit:linkage>
                            <cit:protocol>
                                <gco:CharacterString>OGC:WMS</gco:CharacterString>
                            </cit:protocol>
                            <cit:name>
                                <gco:CharacterString>psc:proj_3948</gco:CharacterString>
                            </cit:name>
                            <cit:description>
                                <gco:CharacterString>proj_3948</gco:CharacterString>
                            </cit:description>
                            <cit:function>
                                <cit:CI_OnLineFunctionCode codeList="http://standards.iso.org/iso/19115/resources/Codelists/cat/codelists.xml#CI_OnLineFunctionCode" codeListValue="download" />
                            </cit:function>
                        </cit:CI_OnlineResource>
                    </mrd:onLine>
                    <mrd:onLine>
                        <cit:CI_OnlineResource>
                            <cit:linkage>
                                <gco:CharacterString>http://localhost:8080/geoserver/psc/wfs</gco:CharacterString>
                            </cit:linkage>
                            <cit:protocol>
                                <gco:CharacterString>OGC:WFS</gco:CharacterString>
                            </cit:protocol>
                            <cit:name>
                                <gco:CharacterString>psc:proj_3948</gco:CharacterString>
                            </cit:name>
                            <cit:description>
                                <gco:CharacterString>proj_3948</gco:CharacterString>
                            </cit:description>
                            <cit:function>
                                <cit:CI_OnLineFunctionCode codeList="http://standards.iso.org/iso/19115/resources/Codelists/cat/codelists.xml#CI_OnLineFunctionCode" codeListValue="download" />
                            </cit:function>
                        </cit:CI_OnlineResource>
                    </mrd:onLine>
                </mrd:MD_DigitalTransferOptions>
            </mrd:transferOptions>
        </mrd:MD_Distribution>
    </mdb:distributionInfo>
</mdb:MD_Metadata>
"""

SAMPLE_19139_WITH_ONLINE_RESOURCES = b"""\
<gmd:MD_Metadata xmlns:gco="http://www.isotc211.org/2005/gco"
                 xmlns:gmd="http://www.isotc211.org/2005/gmd">
   <gmd:distributionInfo>
      <gmd:MD_Distribution>
         <gmd:transferOptions>
            <gmd:MD_DigitalTransferOptions>
               <gmd:onLine>
                  <gmd:CI_OnlineResource>
                     <gmd:linkage>
                        <gmd:URL>http://localhost:8080/geoserver/ogc/features/v1/collections/psc:proj_3948?f=json</gmd:URL>
                     </gmd:linkage>
                     <gmd:protocol>
                        <gco:CharacterString>OGC API Features</gco:CharacterString>
                     </gmd:protocol>
                     <gmd:name>
                        <gco:CharacterString>psc:proj_3948</gco:CharacterString>
                     </gmd:name>
                     <gmd:description>
                        <gco:CharacterString>proj_3948</gco:CharacterString>
                     </gmd:description>
                     <gmd:function>
                        <gmd:CI_OnLineFunctionCode codeList="http://standards.iso.org/iso/19115/resources/Codelists/cat/codelists.xml#CI_OnLineFunctionCode"
                                                   codeListValue="download"/>
                     </gmd:function>
                  </gmd:CI_OnlineResource>
               </gmd:onLine>
               <gmd:onLine>
                  <gmd:CI_OnlineResource>
                     <gmd:linkage>
                        <gmd:URL>http://localhost:8080/geoserver/psc/wms</gmd:URL>
                     </gmd:linkage>
                     <gmd:protocol>
                        <gco:CharacterString>OGC:WMS</gco:CharacterString>
                     </gmd:protocol>
                     <gmd:name>
                        <gco:CharacterString>psc:proj_3948</gco:CharacterString>
                     </gmd:name>
                     <gmd:description>
                        <gco:CharacterString>proj_3948</gco:CharacterString>
                     </gmd:description>
                     <gmd:function>
                        <gmd:CI_OnLineFunctionCode codeList="http://standards.iso.org/iso/19115/resources/Codelists/cat/codelists.xml#CI_OnLineFunctionCode"
                                                   codeListValue="download"/>
                     </gmd:function>
                  </gmd:CI_OnlineResource>
               </gmd:onLine>
               <gmd:onLine>
                  <gmd:CI_OnlineResource>
                     <gmd:linkage>
                        <gmd:URL>http://localhost:8080/geoserver/psc/wfs</gmd:URL>
                     </gmd:linkage>
                     <gmd:protocol>
                        <gco:CharacterString>OGC:WFS</gco:CharacterString>
                     </gmd:protocol>
                     <gmd:name>
                        <gco:CharacterString>psc:proj_3948</gco:CharacterString>
                     </gmd:name>
                     <gmd:description>
                        <gco:CharacterString>proj_3948</gco:CharacterString>
                     </gmd:description>
                     <gmd:function>
                        <gmd:CI_OnLineFunctionCode codeList="http://standards.iso.org/iso/19115/resources/Codelists/cat/codelists.xml#CI_OnLineFunctionCode"
                                                   codeListValue="download"/>
                     </gmd:function>
                  </gmd:CI_OnlineResource>
               </gmd:onLine>
            </gmd:MD_DigitalTransferOptions>
         </gmd:transferOptions>
      </gmd:MD_Distribution>
   </gmd:distributionInfo>
</gmd:MD_Metadata>
"""
