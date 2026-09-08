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
