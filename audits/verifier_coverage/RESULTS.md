# Verifier-coverage audit

Forms: 8 | all fields: 249 | text fields: 219 | critical text fields: 103

## Headline

| Scope | Verified | Total | Coverage |
|---|---:|---:|---:|
| All text fields | 31 | 219 |  14.2% |
| Critical fields | 24 | 103 |  23.3% |

Headline rule: `combined`. Go threshold: >=40% of critical fields.

## Sensitivity to the decision rule

| Rule | All text | Critical | Go (>=40% critical)? |
|---|---:|---:|---|
| conservative | 10.5% | 16.5% | NO-GO |
| combined | 14.2% | 23.3% | NO-GO |
| liberal | 57.1% | 69.9% | GO |

## Best available verifier strength (independent of the rule)

| Strength | All text | Critical |
|---|---:|---:|
| strong | 23 (10.5%) | 17 (16.5%) |
| partial | 58 (26.5%) | 55 (53.4%) |
| medium | 44 (20.1%) | 0 (0.0%) |
| weak | 94 (42.9%) | 31 (30.1%) |
| none | 0 (0.0%) | 0 (0.0%) |

## Per form

| Form | Text | Verified | Coverage | Critical | Crit. verified | Crit. coverage | Extraction |
|---|---:|---:|---:|---:|---:|---:|---|
| cc01_can_cuoc | 30 | 3 |  10.0% | 10 | 1 |  10.0% | verbatim page text; 14 biometric slots collapsed into one non-text entry |
| ct01_cu_tru | 24 | 2 |   8.3% | 16 | 0 |   0.0% | verbatim page text |
| giay_nop_tien_nsnn | 35 | 5 |  14.3% | 9 | 5 |  55.6% | verbatim page text |
| giay_uy_quyen | 31 | 9 |  29.0% | 22 | 9 |  40.9% | verbatim page text |
| hoa_don_gtgt | 22 | 10 |  45.5% | 13 | 9 |  69.2% | legal list of mandatory contents, not a blank form; seller/buyer items split into name/address/MST |
| so_yeu_ly_lich | 43 | 1 |   2.3% | 19 | 0 |   0.0% | model-extracted summary of the page, NOT verbatim; verify against the template file |
| tk1_ts_bhxh | 19 | 0 |   0.0% | 6 | 0 |   0.0% | verbatim page text |
| to_khai_xac_nhan_hon_nhan | 15 | 1 |   6.7% | 8 | 0 |   0.0% | verbatim page text |

## Per field type

| Type | Fields | Verified | Coverage | Best strength seen |
|---|---:|---:|---:|---|
| date | 27 | 0 |   0.0% | partial |
| free_text | 24 | 0 |   0.0% | weak |
| person_name | 23 | 6 |  26.1% | partial |
| address | 17 | 0 |   0.0% | partial |
| organization_name | 15 | 0 |   0.0% | partial |
| id_number | 14 | 1 |   7.1% | partial |
| money_number | 11 | 9 |  81.8% | strong |
| place_name | 7 | 1 |  14.3% | partial |
| doc_number | 7 | 0 |   0.0% | weak |
| admin_unit | 7 | 0 |   0.0% | medium |
| quantity | 6 | 1 |  16.7% | strong |
| year | 6 | 3 |  50.0% | strong |
| gender | 5 | 5 | 100.0% | strong |
| occupation | 5 | 0 |   0.0% | weak |
| ethnicity | 4 | 0 |   0.0% | medium |
| nationality | 4 | 0 |   0.0% | medium |
| phone | 4 | 0 |   0.0% | weak |
| relation | 4 | 0 |   0.0% | medium |
| issuing_authority | 4 | 0 |   0.0% | medium |
| email | 3 | 0 |   0.0% | weak |
| tax_code | 3 | 3 | 100.0% | strong |
| bank_account | 3 | 0 |   0.0% | weak |
| id_number_legacy | 2 | 0 |   0.0% | weak |
| religion | 2 | 0 |   0.0% | medium |
| bank_name | 2 | 0 |   0.0% | medium |
| budget_code | 2 | 0 |   0.0% | medium |
| money_words | 2 | 2 | 100.0% | strong |
| blood_type | 1 | 0 |   0.0% | medium |
| agency_code | 1 | 0 |   0.0% | medium |
| admin_code | 1 | 0 |   0.0% | medium |
| tax_rate | 1 | 0 |   0.0% | medium |
| education_level | 1 | 0 |   0.0% | medium |
| insurance_number | 1 | 0 |   0.0% | weak |

## Where verified coverage comes from

| Verifier | Verified fields it contributes to |
|---|---:|
| V_ARITHMETIC | 10 |
| V_CCCD_CROSS | 9 |
| V_REPEAT | 6 |
| V_SURNAME | 6 |
| V_CLOSED_SET | 5 |
| V_DIGITS_WORDS | 4 |
| V_MST_CHECKSUM | 3 |
| V_CCCD_PROVINCE | 2 |
| V_NUMBER_GRAMMAR | 2 |
| V_GAZETTEER | 1 |

## Unverified critical fields

- `cc01_can_cuoc` / Chủ thể / **Họ, chữ đệm và tên khai sinh** (person_name): V_SYLLABLE(weak), V_SURNAME(partial)
- `cc01_can_cuoc` / Chủ thể / **Tên gọi khác** (person_name): V_SYLLABLE(weak), V_SURNAME(partial)
- `cc01_can_cuoc` / Chủ thể / **Ngày, tháng, năm sinh** (date): V_CALENDAR(weak), V_CCCD_CROSS(partial)
- `cc01_can_cuoc` / Chủ thể / **Nơi thường trú** (address): V_SYLLABLE(weak), V_GAZETTEER(partial)
- `cc01_can_cuoc` / Chủ thể / **Nơi tạm trú** (address): V_SYLLABLE(weak), V_GAZETTEER(partial)
- `cc01_can_cuoc` / Chủ thể / **Nơi ở hiện tại** (address): V_SYLLABLE(weak), V_GAZETTEER(partial)
- `cc01_can_cuoc` / Thân nhân (bảng) / **Họ, chữ đệm và tên khai sinh** (person_name): V_SYLLABLE(weak), V_SURNAME(partial)
- `cc01_can_cuoc` / Thân nhân (bảng) / **Số định danh cá nhân** (id_number): V_CCCD_STRUCT(weak)
- `cc01_can_cuoc` / Ký / **Ngày ... tháng ... năm ...** (date): V_CALENDAR(weak)
- `ct01_cu_tru` / Người kê khai / **Họ, chữ đệm và tên** (person_name): V_SYLLABLE(weak), V_SURNAME(partial)
- `ct01_cu_tru` / Người kê khai / **Ngày, tháng, năm sinh** (date): V_CALENDAR(weak), V_CCCD_CROSS(partial)
- `ct01_cu_tru` / Người kê khai / **Số định danh cá nhân** (id_number): V_CCCD_STRUCT(weak), V_CCCD_CROSS(partial)
- `ct01_cu_tru` / Chủ hộ / **Họ, chữ đệm và tên chủ hộ** (person_name): V_SYLLABLE(weak), V_SURNAME(partial)
- `ct01_cu_tru` / Chủ hộ / **Số định danh cá nhân của chủ hộ** (id_number): V_CCCD_STRUCT(weak)
- `ct01_cu_tru` / Thành viên hộ (bảng) / **Họ, chữ đệm và tên** (person_name): V_SYLLABLE(weak), V_SURNAME(partial)
- `ct01_cu_tru` / Thành viên hộ (bảng) / **Ngày, tháng, năm sinh** (date): V_CALENDAR(weak), V_CCCD_CROSS(partial)
- `ct01_cu_tru` / Thành viên hộ (bảng) / **Số định danh cá nhân** (id_number): V_CCCD_STRUCT(weak), V_CCCD_CROSS(partial)
- `ct01_cu_tru` / Ký / **Ngày ký (chủ hộ)** (date): V_CALENDAR(weak)
- `ct01_cu_tru` / Ký / **Ngày ký (chủ sở hữu chỗ ở)** (date): V_CALENDAR(weak)
- `ct01_cu_tru` / Chủ sở hữu chỗ ở / **Họ và tên (VNeID)** (person_name): V_SYLLABLE(weak), V_SURNAME(partial)
- `ct01_cu_tru` / Chủ sở hữu chỗ ở / **Số định danh cá nhân (VNeID)** (id_number): V_CCCD_STRUCT(weak)
- `ct01_cu_tru` / Ký / **Ngày ký (cha, mẹ, giám hộ)** (date): V_CALENDAR(weak)
- `ct01_cu_tru` / Cha, mẹ, giám hộ / **Họ và tên (VNeID)** (person_name): V_SYLLABLE(weak), V_SURNAME(partial)
- `ct01_cu_tru` / Cha, mẹ, giám hộ / **Số định danh cá nhân (VNeID)** (id_number): V_CCCD_STRUCT(weak)
- `ct01_cu_tru` / Ký / **Ngày ký (người kê khai)** (date): V_CALENDAR(weak)
- `giay_nop_tien_nsnn` / Người nộp thuế / **Địa chỉ** (address): V_SYLLABLE(weak), V_GAZETTEER(partial)
- `giay_nop_tien_nsnn` / Người nộp thay / **Địa chỉ** (address): V_SYLLABLE(weak), V_GAZETTEER(partial)
- `giay_nop_tien_nsnn` / Ký / **Ngày ... tháng ... năm ... (người nộp)** (date): V_CALENDAR(weak)
- `giay_nop_tien_nsnn` / Ký / **Ngày ... tháng ... năm ... (NH/KBNN)** (date): V_CALENDAR(weak)
- `giay_uy_quyen` / Mở đầu / **Hôm nay, ngày ... tháng ... năm ..., tại** (date): V_CALENDAR(weak)
- `giay_uy_quyen` / Bên ủy quyền 1 / **Ông** (person_name): V_SYLLABLE(weak), V_SURNAME(partial)
- `giay_uy_quyen` / Bên ủy quyền 1 / **CMND/CCCD/Hộ chiếu số** (id_number): V_CCCD_STRUCT(weak), V_CCCD_CROSS(partial)
- `giay_uy_quyen` / Bên ủy quyền 1 / **cấp ngày** (date): V_CALENDAR(weak)
- `giay_uy_quyen` / Bên ủy quyền 1 / **Hộ khẩu thường trú** (address): V_SYLLABLE(weak), V_GAZETTEER(partial)
- `giay_uy_quyen` / Bên ủy quyền 2 / **Cùng vợ là bà** (person_name): V_SYLLABLE(weak), V_SURNAME(partial)
- `giay_uy_quyen` / Bên ủy quyền 2 / **CMND/CCCD/Hộ chiếu số** (id_number): V_CCCD_STRUCT(weak), V_CCCD_CROSS(partial)
- `giay_uy_quyen` / Bên ủy quyền 2 / **cấp ngày** (date): V_CALENDAR(weak)
- `giay_uy_quyen` / Bên ủy quyền 2 / **Hộ khẩu thường trú** (address): V_SYLLABLE(weak), V_GAZETTEER(partial)
- `giay_uy_quyen` / Bên được ủy quyền / **CMND/CCCD/Hộ chiếu số** (id_number): V_CCCD_STRUCT(weak), V_CCCD_CROSS(partial)
- `giay_uy_quyen` / Bên được ủy quyền / **cấp ngày** (date): V_CALENDAR(weak)
- `giay_uy_quyen` / Bên được ủy quyền / **Hộ khẩu thường trú** (address): V_SYLLABLE(weak), V_GAZETTEER(partial)
- `giay_uy_quyen` / Nội dung / **Điều 3. Thù lao ủy quyền** (money_number): V_FORMAT(weak)
- `hoa_don_gtgt` / Người bán / **Địa chỉ người bán** (address): V_SYLLABLE(weak), V_GAZETTEER(partial)
- `hoa_don_gtgt` / Người mua / **Địa chỉ người mua** (address): V_SYLLABLE(weak), V_GAZETTEER(partial)
- `hoa_don_gtgt` / Ký / **Thời điểm lập hóa đơn** (date): V_CALENDAR(weak)
- `hoa_don_gtgt` / Ký / **Thời điểm ký số** (date): V_CALENDAR(weak)
- `so_yeu_ly_lich` / Bản thân / **Họ và tên (chữ in hoa)** (person_name): V_SYLLABLE(weak), V_SURNAME(partial)
- `so_yeu_ly_lich` / Bản thân / **Sinh ngày ... tháng ... năm** (date): V_CALENDAR(weak), V_CCCD_CROSS(partial)
- `so_yeu_ly_lich` / Bản thân / **Nơi đăng ký hộ khẩu thường trú** (address): V_SYLLABLE(weak), V_GAZETTEER(partial)
- `so_yeu_ly_lich` / Bản thân / **Chỗ ở hiện nay** (address): V_SYLLABLE(weak), V_GAZETTEER(partial)
- `so_yeu_ly_lich` / Bản thân / **Số CCCD/CMND** (id_number): V_CCCD_STRUCT(weak), V_CCCD_CROSS(partial)
- `so_yeu_ly_lich` / Bản thân / **cấp ngày** (date): V_CALENDAR(weak)
- `so_yeu_ly_lich` / Bản thân / **Kết nạp Đoàn ngày** (date): V_CALENDAR(weak)
- `so_yeu_ly_lich` / Bản thân / **Kết nạp Đảng ngày** (date): V_CALENDAR(weak)
- `so_yeu_ly_lich` / Cha / **Họ và tên cha** (person_name): V_SYLLABLE(weak), V_SURNAME(partial)
- `so_yeu_ly_lich` / Cha / **Năm sinh** (year): V_RANGE(weak)
- `so_yeu_ly_lich` / Cha / **Chỗ ở hiện nay** (address): V_SYLLABLE(weak), V_GAZETTEER(partial)
- `so_yeu_ly_lich` / Mẹ / **Họ và tên mẹ** (person_name): V_SYLLABLE(weak), V_SURNAME(partial)
- `so_yeu_ly_lich` / Mẹ / **Năm sinh** (year): V_RANGE(weak)
- `so_yeu_ly_lich` / Mẹ / **Chỗ ở hiện nay** (address): V_SYLLABLE(weak), V_GAZETTEER(partial)
- `so_yeu_ly_lich` / Anh chị em (3 dòng) / **Họ và tên anh/chị em ruột** (person_name): V_SYLLABLE(weak), V_SURNAME(partial)
- `so_yeu_ly_lich` / Anh chị em (3 dòng) / **Năm sinh** (year): V_RANGE(weak)
- `so_yeu_ly_lich` / Đào tạo (bảng) / **Từ tháng năm đến tháng năm** (date): V_CALENDAR(weak)
- `so_yeu_ly_lich` / Công tác (bảng) / **Từ tháng năm đến tháng năm** (date): V_CALENDAR(weak)
- `so_yeu_ly_lich` / Ký / **Tp ..., ngày ... tháng ... năm 20..** (date): V_CALENDAR(weak)
- `tk1_ts_bhxh` / Thông tin chung / **[01] Họ và tên** (person_name): V_SYLLABLE(weak), V_SURNAME(partial)
- `tk1_ts_bhxh` / Thông tin chung / **[03] Ngày, tháng, năm sinh** (date): V_CALENDAR(weak), V_CCCD_CROSS(partial)
- `tk1_ts_bhxh` / Thông tin chung / **[04] Số CCCD/ĐDCN/hộ chiếu** (id_number): V_CCCD_STRUCT(weak), V_CCCD_CROSS(partial)
- `tk1_ts_bhxh` / Thông tin chung / **[11.1] số nhà, đường/phố, thôn/xóm** (address): V_SYLLABLE(weak), V_GAZETTEER(partial)
- `tk1_ts_bhxh` / Bổ sung / **[12] Mức tiền đóng** (money_number): V_FORMAT(weak)
- `tk1_ts_bhxh` / Ký / **..., ngày ... tháng ... năm ...** (date): V_CALENDAR(weak)
- `to_khai_xac_nhan_hon_nhan` / Người yêu cầu / **Họ, chữ đệm, tên người yêu cầu** (person_name): V_SYLLABLE(weak), V_SURNAME(partial)
- `to_khai_xac_nhan_hon_nhan` / Người yêu cầu / **Nơi cư trú** (address): V_SYLLABLE(weak), V_GAZETTEER(partial)
- `to_khai_xac_nhan_hon_nhan` / Người yêu cầu / **Giấy tờ tùy thân** (id_number): V_CCCD_STRUCT(weak)
- `to_khai_xac_nhan_hon_nhan` / Người được cấp / **Họ, chữ đệm, tên** (person_name): V_SYLLABLE(weak), V_SURNAME(partial)
- `to_khai_xac_nhan_hon_nhan` / Người được cấp / **Ngày, tháng, năm sinh** (date): V_CALENDAR(weak), V_CCCD_CROSS(partial)
- `to_khai_xac_nhan_hon_nhan` / Người được cấp / **Nơi cư trú** (address): V_SYLLABLE(weak), V_GAZETTEER(partial)
- `to_khai_xac_nhan_hon_nhan` / Người được cấp / **Giấy tờ tùy thân** (id_number): V_CCCD_STRUCT(weak), V_CCCD_CROSS(partial)
- `to_khai_xac_nhan_hon_nhan` / Ký / **Làm tại ..., ngày ... tháng ... năm ...** (date): V_CALENDAR(weak)

# Direction A: dossier-level coverage

Same fields and rules as above; cross-document hits are added per scenario.

| Scenario | What is reachable |
|---|---|
| `single_form` | form alone (the earlier audit) |
| `archived_min` | paper backlog, legally required dossier parts + public MST registry |
| `archived_typical` | paper backlog, plus customary copies (CCCD/khai sinh in job dossiers) |
| `live_scan` | counter intake that photographs the presented card / tax notice |
| `live_chip` | counter intake that also reads the card chip over NFC |
| `gov_db` | agency with CSDL dân cư / e-invoice portal access |

## Critical-field coverage by scenario and rule

| Scenario | conservative | combined | liberal | All text (combined) | Go (combined >=40%)? |
|---|---:|---:|---:|---:|---|
| `single_form` | 16.5% | 23.3% | 69.9% | 14.2% | NO-GO |
| `archived_min` | 31.1% | 37.9% | 73.8% | 24.7% | NO-GO |
| `archived_typical` | 38.8% | 47.6% | 76.7% | 31.1% | GO |
| `live_scan` | 53.4% | 64.1% | 77.7% | 42.9% | GO |
| `live_chip` | 53.4% | 65.0% | 77.7% | 45.2% | GO |
| `gov_db` | 69.9% | 76.7% | 82.5% | 54.3% | GO |

### Excluding signing dates (13 fields), `combined` rule

| Scenario | Critical w/o signing dates |
|---|---:|
| `single_form` | 26.7% |
| `archived_min` | 43.3% |
| `archived_typical` | 54.4% |
| `live_scan` | 73.3% |
| `live_chip` | 74.4% |
| `gov_db` | 85.6% |

## Critical coverage per form (`combined` rule)

| Form | Critical | single_form | archived_min | archived_typical | live_scan | live_chip | gov_db |
|---|---:|---:|---:|---:|---:|---:|---:|
| cc01_can_cuoc | 10 | 10.0% | 10.0% | 10.0% | 40.0% | 50.0% | 70.0% |
| ct01_cu_tru | 16 | 0.0% | 6.2% | 6.2% | 25.0% | 25.0% | 75.0% |
| giay_nop_tien_nsnn | 9 | 55.6% | 66.7% | 66.7% | 66.7% | 66.7% | 66.7% |
| giay_uy_quyen | 22 | 40.9% | 90.9% | 90.9% | 90.9% | 90.9% | 90.9% |
| hoa_don_gtgt | 13 | 69.2% | 84.6% | 84.6% | 84.6% | 84.6% | 100.0% |
| so_yeu_ly_lich | 19 | 0.0% | 0.0% | 52.6% | 52.6% | 52.6% | 52.6% |
| tk1_ts_bhxh | 6 | 0.0% | 0.0% | 0.0% | 66.7% | 66.7% | 66.7% |
| to_khai_xac_nhan_hon_nhan | 8 | 0.0% | 0.0% | 0.0% | 87.5% | 87.5% | 87.5% |

## Critical coverage per field type (`combined` rule)

| Type | Fields | single_form | archived_min | archived_typical | live_scan | live_chip | gov_db |
|---|---:|---:|---:|---:|---:|---:|---:|
| date | 27 | 0.0% | 11.1% | 18.5% | 33.3% | 33.3% | 44.4% |
| person_name | 23 | 26.1% | 39.1% | 52.2% | 73.9% | 78.3% | 91.3% |
| address | 17 | 0.0% | 35.3% | 47.1% | 70.6% | 70.6% | 76.5% |
| id_number | 14 | 7.1% | 28.6% | 35.7% | 64.3% | 64.3% | 100.0% |
| money_number | 11 | 81.8% | 81.8% | 81.8% | 81.8% | 81.8% | 81.8% |
| year | 6 | 50.0% | 50.0% | 83.3% | 83.3% | 83.3% | 83.3% |
| tax_code | 3 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| money_words | 2 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

## Unverified critical fields in `archived_typical`

- `cc01_can_cuoc` / Chủ thể / **Họ, chữ đệm và tên khai sinh** (person_name)
- `cc01_can_cuoc` / Chủ thể / **Tên gọi khác** (person_name)
- `cc01_can_cuoc` / Chủ thể / **Ngày, tháng, năm sinh** (date)
- `cc01_can_cuoc` / Chủ thể / **Nơi thường trú** (address)
- `cc01_can_cuoc` / Chủ thể / **Nơi tạm trú** (address)
- `cc01_can_cuoc` / Chủ thể / **Nơi ở hiện tại** (address)
- `cc01_can_cuoc` / Thân nhân (bảng) / **Họ, chữ đệm và tên khai sinh** (person_name)
- `cc01_can_cuoc` / Thân nhân (bảng) / **Số định danh cá nhân** (id_number)
- `cc01_can_cuoc` / Ký / **Ngày ... tháng ... năm ...** (date)
- `ct01_cu_tru` / Người kê khai / **Họ, chữ đệm và tên** (person_name)
- `ct01_cu_tru` / Người kê khai / **Ngày, tháng, năm sinh** (date)
- `ct01_cu_tru` / Người kê khai / **Số định danh cá nhân** (id_number)
- `ct01_cu_tru` / Chủ hộ / **Họ, chữ đệm và tên chủ hộ** (person_name)
- `ct01_cu_tru` / Chủ hộ / **Số định danh cá nhân của chủ hộ** (id_number)
- `ct01_cu_tru` / Thành viên hộ (bảng) / **Họ, chữ đệm và tên** (person_name)
- `ct01_cu_tru` / Thành viên hộ (bảng) / **Ngày, tháng, năm sinh** (date)
- `ct01_cu_tru` / Thành viên hộ (bảng) / **Số định danh cá nhân** (id_number)
- `ct01_cu_tru` / Ký / **Ngày ký (chủ hộ)** (date)
- `ct01_cu_tru` / Ký / **Ngày ký (chủ sở hữu chỗ ở)** (date)
- `ct01_cu_tru` / Chủ sở hữu chỗ ở / **Số định danh cá nhân (VNeID)** (id_number)
- `ct01_cu_tru` / Ký / **Ngày ký (cha, mẹ, giám hộ)** (date)
- `ct01_cu_tru` / Cha, mẹ, giám hộ / **Họ và tên (VNeID)** (person_name)
- `ct01_cu_tru` / Cha, mẹ, giám hộ / **Số định danh cá nhân (VNeID)** (id_number)
- `ct01_cu_tru` / Ký / **Ngày ký (người kê khai)** (date)
- `giay_nop_tien_nsnn` / Người nộp thay / **Địa chỉ** (address)
- `giay_nop_tien_nsnn` / Ký / **Ngày ... tháng ... năm ... (người nộp)** (date)
- `giay_nop_tien_nsnn` / Ký / **Ngày ... tháng ... năm ... (NH/KBNN)** (date)
- `giay_uy_quyen` / Mở đầu / **Hôm nay, ngày ... tháng ... năm ..., tại** (date)
- `giay_uy_quyen` / Nội dung / **Điều 3. Thù lao ủy quyền** (money_number)
- `hoa_don_gtgt` / Ký / **Thời điểm lập hóa đơn** (date)
- `hoa_don_gtgt` / Ký / **Thời điểm ký số** (date)
- `so_yeu_ly_lich` / Bản thân / **Kết nạp Đoàn ngày** (date)
- `so_yeu_ly_lich` / Bản thân / **Kết nạp Đảng ngày** (date)
- `so_yeu_ly_lich` / Cha / **Chỗ ở hiện nay** (address)
- `so_yeu_ly_lich` / Mẹ / **Chỗ ở hiện nay** (address)
- `so_yeu_ly_lich` / Anh chị em (3 dòng) / **Họ và tên anh/chị em ruột** (person_name)
- `so_yeu_ly_lich` / Anh chị em (3 dòng) / **Năm sinh** (year)
- `so_yeu_ly_lich` / Đào tạo (bảng) / **Từ tháng năm đến tháng năm** (date)
- `so_yeu_ly_lich` / Công tác (bảng) / **Từ tháng năm đến tháng năm** (date)
- `so_yeu_ly_lich` / Ký / **Tp ..., ngày ... tháng ... năm 20..** (date)
- `tk1_ts_bhxh` / Thông tin chung / **[01] Họ và tên** (person_name)
- `tk1_ts_bhxh` / Thông tin chung / **[03] Ngày, tháng, năm sinh** (date)
- `tk1_ts_bhxh` / Thông tin chung / **[04] Số CCCD/ĐDCN/hộ chiếu** (id_number)
- `tk1_ts_bhxh` / Thông tin chung / **[11.1] số nhà, đường/phố, thôn/xóm** (address)
- `tk1_ts_bhxh` / Bổ sung / **[12] Mức tiền đóng** (money_number)
- `tk1_ts_bhxh` / Ký / **..., ngày ... tháng ... năm ...** (date)
- `to_khai_xac_nhan_hon_nhan` / Người yêu cầu / **Họ, chữ đệm, tên người yêu cầu** (person_name)
- `to_khai_xac_nhan_hon_nhan` / Người yêu cầu / **Nơi cư trú** (address)
- `to_khai_xac_nhan_hon_nhan` / Người yêu cầu / **Giấy tờ tùy thân** (id_number)
- `to_khai_xac_nhan_hon_nhan` / Người được cấp / **Họ, chữ đệm, tên** (person_name)
- `to_khai_xac_nhan_hon_nhan` / Người được cấp / **Ngày, tháng, năm sinh** (date)
- `to_khai_xac_nhan_hon_nhan` / Người được cấp / **Nơi cư trú** (address)
- `to_khai_xac_nhan_hon_nhan` / Người được cấp / **Giấy tờ tùy thân** (id_number)
- `to_khai_xac_nhan_hon_nhan` / Ký / **Làm tại ..., ngày ... tháng ... năm ...** (date)

## Unverified critical fields in `live_scan`

- `cc01_can_cuoc` / Chủ thể / **Tên gọi khác** (person_name)
- `cc01_can_cuoc` / Chủ thể / **Nơi tạm trú** (address)
- `cc01_can_cuoc` / Chủ thể / **Nơi ở hiện tại** (address)
- `cc01_can_cuoc` / Thân nhân (bảng) / **Họ, chữ đệm và tên khai sinh** (person_name)
- `cc01_can_cuoc` / Thân nhân (bảng) / **Số định danh cá nhân** (id_number)
- `cc01_can_cuoc` / Ký / **Ngày ... tháng ... năm ...** (date)
- `ct01_cu_tru` / Chủ hộ / **Họ, chữ đệm và tên chủ hộ** (person_name)
- `ct01_cu_tru` / Chủ hộ / **Số định danh cá nhân của chủ hộ** (id_number)
- `ct01_cu_tru` / Thành viên hộ (bảng) / **Họ, chữ đệm và tên** (person_name)
- `ct01_cu_tru` / Thành viên hộ (bảng) / **Ngày, tháng, năm sinh** (date)
- `ct01_cu_tru` / Thành viên hộ (bảng) / **Số định danh cá nhân** (id_number)
- `ct01_cu_tru` / Ký / **Ngày ký (chủ hộ)** (date)
- `ct01_cu_tru` / Ký / **Ngày ký (chủ sở hữu chỗ ở)** (date)
- `ct01_cu_tru` / Chủ sở hữu chỗ ở / **Số định danh cá nhân (VNeID)** (id_number)
- `ct01_cu_tru` / Ký / **Ngày ký (cha, mẹ, giám hộ)** (date)
- `ct01_cu_tru` / Cha, mẹ, giám hộ / **Họ và tên (VNeID)** (person_name)
- `ct01_cu_tru` / Cha, mẹ, giám hộ / **Số định danh cá nhân (VNeID)** (id_number)
- `ct01_cu_tru` / Ký / **Ngày ký (người kê khai)** (date)
- `giay_nop_tien_nsnn` / Người nộp thay / **Địa chỉ** (address)
- `giay_nop_tien_nsnn` / Ký / **Ngày ... tháng ... năm ... (người nộp)** (date)
- `giay_nop_tien_nsnn` / Ký / **Ngày ... tháng ... năm ... (NH/KBNN)** (date)
- `giay_uy_quyen` / Mở đầu / **Hôm nay, ngày ... tháng ... năm ..., tại** (date)
- `giay_uy_quyen` / Nội dung / **Điều 3. Thù lao ủy quyền** (money_number)
- `hoa_don_gtgt` / Ký / **Thời điểm lập hóa đơn** (date)
- `hoa_don_gtgt` / Ký / **Thời điểm ký số** (date)
- `so_yeu_ly_lich` / Bản thân / **Kết nạp Đoàn ngày** (date)
- `so_yeu_ly_lich` / Bản thân / **Kết nạp Đảng ngày** (date)
- `so_yeu_ly_lich` / Cha / **Chỗ ở hiện nay** (address)
- `so_yeu_ly_lich` / Mẹ / **Chỗ ở hiện nay** (address)
- `so_yeu_ly_lich` / Anh chị em (3 dòng) / **Họ và tên anh/chị em ruột** (person_name)
- `so_yeu_ly_lich` / Anh chị em (3 dòng) / **Năm sinh** (year)
- `so_yeu_ly_lich` / Đào tạo (bảng) / **Từ tháng năm đến tháng năm** (date)
- `so_yeu_ly_lich` / Công tác (bảng) / **Từ tháng năm đến tháng năm** (date)
- `so_yeu_ly_lich` / Ký / **Tp ..., ngày ... tháng ... năm 20..** (date)
- `tk1_ts_bhxh` / Bổ sung / **[12] Mức tiền đóng** (money_number)
- `tk1_ts_bhxh` / Ký / **..., ngày ... tháng ... năm ...** (date)
- `to_khai_xac_nhan_hon_nhan` / Ký / **Làm tại ..., ngày ... tháng ... năm ...** (date)
